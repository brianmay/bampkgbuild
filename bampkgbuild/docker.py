import os
import logging.config
import subprocess
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import List, Optional, Iterator, Any, Tuple

logger = logging.getLogger(__name__)


class docker_container():
    def __init__(self, container: str, gpg: bool) -> None:
        self.container = container
        self.gpg = gpg

    def _get_params(self, cmd: List[str], user: Optional[str], cwd: Optional[str]) -> List[str]:
        env = {}
        params = [
                "podman",
                "exec",
                "-ti",
            ]

        if user is not None:
            params.extend(["--user", user])
            env["USER"] = user
        else:
            params.extend(["--user", str(os.getuid())])
            env["USER"] = str(os.getlogin())

        if cwd is not None:
            params.extend(["--workdir", cwd])

        if self.gpg:
            params.extend(["--env", "GNUPGHOME=/gpg"])

        for key, value in env.items():
            params.extend(["--env", f"{key}={value}"])

        params.append(self.container)
        params.extend(cmd)
        return params

    def check_call(self, cmd: List[str], user: Optional[str]=None, root: bool=False, cwd:  Optional[str]=None) -> int:
        if root:
            user = "root"
        params = self._get_params(cmd, user, cwd)
        return check_call(params)

    def check_output(self, cmd: List[str], user: Optional[str]=None, root=False, cwd=None) -> bytes:
        if root:
            user = "root"
        params = self._get_params(cmd, user, cwd)
        return check_output(params)

    @contextmanager
    def create_file(self, whence: str, user: Optional[str]=None) -> Iterator[Any]:
        with NamedTemporaryFile() as tmp_file:
            yield tmp_file
            tmp_file.flush()
            check_call(
                [
                    'docker',
                    'cp',
                    tmp_file.name,
                    f"{self.container}:{whence}",
                ]
            )

    def get_files(self, src: str, dst: str) -> None:
        check_call(
            [
                'docker',
                'cp',
                f"{self.container}:{src}",
                dst
            ]
        )


class docker():
    def __init__(self, chroot_name: str, gpg: bool=False, volume: Optional[Tuple[str,str]]=None) -> None:
        self.chroot_name = chroot_name
        self.gpg = gpg
        self.volume = volume

    def __enter__(self) -> docker_container:
        params = [
            "podman",
            "create",
            "-t",
            "-i",
            "-v", "/tmp:/tmp",
        ]

        volume = self.volume
        if volume is not None:
            params.extend(["--volume", f"{volume[0]}:{volume[1]}"])

        if self.gpg:
            gpg_dir = os.environ['GNUPGHOME']
            params.extend(["--volume", f"{gpg_dir}:/gpg"])

        params.extend(["--userns", "keep-id"])

        params.append(self.chroot_name)
        self.container = check_output(params).strip().decode()

        check_call(
            [
                "podman",
                "start",
                self.container,
            ]
        )

        docker = docker_container(self.container, self.gpg)
        return docker

    def __exit__(self, type: str, value: str, traceback: str) -> None:
        check_call(
            [
                "podman",
                "kill",
                self.container,
            ]
        )

        check_call(
            [
                "podman",
                "rm",
                self.container,
            ]
        )


def check_call(cmd: List[str]) -> int:
    logger.debug(" ".join(cmd))
    return subprocess.check_call(cmd)


def check_output(cmd: List[str]) -> bytes:
    logger.debug(" ".join(cmd))
    return subprocess.check_output(cmd)
