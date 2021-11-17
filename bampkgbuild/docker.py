import os
import logging.config
import subprocess
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)


class docker_container():
    def __init__(self, container):
        self.container = container

    def _get_params(self, cmd, user, cwd):
        env = {}
        params = [
                "docker",
                "exec",
                "-ti",
            ]

        if user is not None:
            params.extend(["--user", user])
            env["USER"] = user
        else:
            params.extend(["--user", str(os.getuid())])
            env["USER"] = str(os.getuid())

        if cwd is not None:
            params.extend(["--workdir", cwd])

        for key, value in env.items():
            params.extend(["-e", f"{key}={value}"])

        params.append(self.container)
        params.extend(cmd)
        return params

    def check_call(self, cmd, user=None, root=False, cwd=None):
        if root:
            user = "root"
        params = self._get_params(cmd, user, cwd)
        return check_call(params)

    def check_output(self, cmd, user=None, root=False, cwd=None):
        if root:
            user = "root"
        params = self._get_params(cmd, user, cwd)
        return check_output(params)

    @contextmanager
    def create_file(self, whence, user=None):
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

    def get_files(self, src, dst):
        check_call(
            [
                'docker',
                'cp',
                f"{self.container}:{src}",
                dst
            ]
        )


class docker():
    def __init__(self, chroot_name):
        self.chroot_name = chroot_name

    def __enter__(self):
        self.container = check_output([
            "docker",
            "create",
            "-t",
            "-i",
            "-v", "/tmp:/tmp",
            self.chroot_name,
        ]).strip().decode()

        check_call(
            [
                "docker",
                "start",
                self.container,
            ]
        )

        docker = docker_container(self.container)
        return docker

    def __exit__(self, type, value, traceback):
        check_call(
            [
                "docker",
                "kill",
                self.container,
            ]
        )

        check_call(
            [
                "docker",
                "rm",
                self.container,
            ]
        )


def check_call(cmd):
    logger.debug(" ".join(cmd))
    return subprocess.check_call(cmd)


def check_output(cmd):
    logger.debug(" ".join(cmd))
    return subprocess.check_output(cmd)
