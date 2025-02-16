#!/usr/bin/python3
import argparse
import sys
import os
import os.path
import tempfile
import shutil
import subprocess
import re
from email.utils import formatdate
from debian import deb822
from debian import changelog
from contextlib import contextmanager
import logging.config
from bampkgbuild.docker import docker
from colorlog import ColoredFormatter
from typing import List, Optional, Iterator


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    formatter = ColoredFormatter(
        "\n%(log_color)s%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%m-%d %H:%M",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        },
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    root = logging.getLogger("")
    root.setLevel(logging.DEBUG)
    root.addHandler(console)


def check_call(cmd: List[str]) -> int:
    logger.debug(" ".join(cmd))
    return subprocess.check_call(cmd)


def deb_build_src(src_dir: str, chroot_name: str) -> str:
    changelog_file = os.path.join(src_dir, "debian/changelog")
    cl = changelog.Changelog(open(changelog_file))
    parent_dir = os.path.join(src_dir, "..")
    parent_abs = os.path.abspath(parent_dir)

    rm_file_list = ["debian/files"]
    for rm_file in rm_file_list:
        path = os.path.join(src_dir, rm_file)
        try:
            os.remove(path)
        except FileNotFoundError:
            # ignore
            pass

    src_abs = os.path.abspath(src_dir)
    src_name = os.path.basename(src_abs)

    if os.path.isdir(os.path.join(src_abs, ".git")):
        with docker(chroot_name, volume=(parent_abs, "/build")) as chroot:
            chroot.check_call(
                [
                    "gbp",
                    "buildpackage",
                    # "--git-ignore-branch", "--git-ignore-new",
                    "--git-builder=debuild --no-lintian -i -I -S -nc -uc -us",
                    "--no-check-builddeps",
                ],
                cwd=os.path.join("/build", src_name),
            )

    else:
        with docker(chroot_name, volume=(parent_abs, "/build")) as chroot:
            chroot.check_call(["dpkg-source", "-b", src_name], cwd=parent_abs)

    # remove epoch for filename
    version = re.sub(r"^\d+:", "", str(cl.version), 1)
    dsc_file = "%s_%s.dsc" % (cl.package, version)
    dsc_file = os.path.join(parent_dir, dsc_file)
    return dsc_file


def deb_copy_source(tmp_dir: str, dsc_path: str) -> str:
    src_dir = os.path.dirname(dsc_path)
    dst_dir = tmp_dir
    dsc_file = os.path.basename(dsc_path)

    d = deb822.Dsc(open(dsc_path))

    src_path = dsc_path
    dst_path = os.path.join(dst_dir, dsc_file)
    shutil.copyfile(src_path, dst_path)

    for f in d["files"]:
        src_path = os.path.join(src_dir, f["name"])
        dst_path = os.path.join(dst_dir, f["name"])
        shutil.copyfile(src_path, dst_path)

    dsc_path = os.path.join(dst_dir, dsc_file)
    return dsc_path


def deb_update_source(
    tmp_dir: str, dsc_path: str, distribution: str, add_to_version: str
) -> str:
    dsc_file = os.path.basename(dsc_path)
    build_dir = os.path.join(tmp_dir, "source")

    with chdir(tmp_dir):
        check_call(["dpkg-source", "-x", dsc_file, build_dir])

    changelog_file = "debian/changelog"
    changelog_path = os.path.join(build_dir, changelog_file)

    cl = changelog.Changelog(open(changelog_path))

    first_block = cl[0]
    version = str(first_block.version)

    write_changelog = False
    m = re.search(r"^(.*)(~.*)\+(\d+)$", version)
    if m is not None:
        version_prefix = m.group(1)
        offset = m.group(3)
        new_version = version_prefix + add_to_version + "+" + offset

        if version != new_version or first_block.distributions != distribution:
            write_changelog = True
            first_block.version = new_version
            first_block.distributions = distribution
    else:
        new_version = version + add_to_version + "+1"

        write_changelog = True
        cl.new_block(
            package=cl.package,
            version=new_version,
            distributions=distribution,
            urgency="low",
            author="Brian May <bam@debian.org>",
            date=formatdate(),
        )
        cl.add_change("")
        cl.add_change("  * Rebuild for %s." % distribution)
        cl.add_change("")

    if write_changelog:
        cl.write_to_open_file(open(changelog_path, "w"))

    control_file = "debian/control"
    control_path = os.path.join(build_dir, control_file)

    control_file_tmp = "debian/control.tmp"
    control_path_tmp = os.path.join(build_dir, control_file_tmp)

    with open(control_path, "rb") as in_file:
        with open(control_path_tmp, "wb") as out_file:
            for d in deb822.Deb822.iter_paragraphs(in_file):
                d["Bugs"] = "mailto:Brian May <brian@linuxpenguins.xyz>"
                d.dump(out_file)
                out_file.write(b"\n")

    os.rename(control_path_tmp, control_path)

    with chdir(tmp_dir):
        check_call(["dpkg-source", "-b", "source"])

    version = re.sub(r"^\d+:", "", str(cl.version), 1)
    dsc_file = "%s_%s.dsc" % (cl.package, version)
    dsc_path = os.path.join(tmp_dir, dsc_file)

    return dsc_path


def deb_build(
    tmp_dir: str,
    dsc_path: str,
    chroot_name: str,
    distribution: str,
    architecture: str,
    arch_any: bool,
    arch_all: bool,
    source: bool,
    extra_repo: Optional[str],
) -> Optional[str]:
    dst_dir = os.path.join(tmp_dir, "build", architecture)
    dsc_path = os.path.abspath(dsc_path)
    build_dir = os.path.join(dst_dir, "source")

    params = [
        "dpkg-buildpackage",
        "--unsigned-source",
        "--unsigned-changes",
        "--changes-option=-DDistribution=%s" % distribution,
        "-sa",
    ]

    build = []
    if source:
        build.append("source")
    if arch_any:
        build.append("any")
    if arch_all:
        build.append("all")

    if len(build) == 0:
        raise RuntimeError("Nothing to build")

    params.append("--build=" + ",".join(build))

    with docker(chroot_name) as chroot:
        if extra_repo is not None:
            name = "/etc/apt/sources.list.d/extra_repo.list"
            with chroot.create_file(name, user="root") as f:
                data = "%s\n" % (extra_repo)
                f.write(data.encode("ASCII"))

        try:
            chroot.check_call(["mkdir", "-p", dst_dir])
            chroot.check_call(["dpkg-source", "-x", dsc_path, build_dir], cwd=dst_dir)
            chroot.check_call(["apt-get", "update", "--yes"], root=True)
            chroot.check_call(["apt-get", "upgrade", "--yes"], root=True)
            chroot.check_call(["apt-get", "build-dep", "--yes", build_dir], root=True)
            chroot.check_call(params, cwd=build_dir)
        except Exception:
            chroot.check_call(["bash"], cwd=build_dir, root=True)
            raise

    changes_file = None
    for name in os.listdir(dst_dir):
        if name.endswith(".changes"):
            if changes_file is not None:
                raise RuntimeError("Found more then one .changes files")
            changes_file = os.path.join(dst_dir, name)

    if changes_file is None:
        return None

    return changes_file


def deb_sign(changes_file: str, chroot_name: str) -> None:
    with docker(chroot_name, gpg=True) as chroot:
        try:
            chroot.check_call(["debsign", changes_file])
        except subprocess.CalledProcessError:
            print("Push any key to try signing again.")
            sys.stdin.readline()
            chroot.check_call(["debsign", changes_file])


def deb_lint(changes_file: str, chroot_name: str) -> None:
    with docker(chroot_name) as chroot:
        chroot.check_call(["apt-get", "update", "--yes"], root=True)
        chroot.check_call(["apt-get", "upgrade", "--yes"], root=True)
        chroot.check_call(
            [
                "apt-get",
                "--yes",
                "-oDpkg::Options::=--force-confold",
                "install",
                "lintian",
            ],
            root=True,
        )
        #        chroot.check_call([
        #            "apt-get", "--yes", "-t", "experimental",
        #            "install", "lintian4python"], root=True)
        chroot.check_call(["lintian", changes_file])


#        chroot.check_call(["lintian4py", changes_file])


def deb_test(
    changes_file: str, chroot_name: str, test_mode: str, extra_repo: Optional[str]
) -> None:
    if test_mode == "none":
        return
    elif test_mode == "manual_no_unpack":
        build_dir = os.path.dirname(changes_file)
        with docker(chroot_name) as chroot:
            chroot.check_call(["bash"], cwd=build_dir, root=True)
        return

    build_dir = os.path.dirname(changes_file)
    d = deb822.Changes(open(changes_file))

    debs = []
    for f in d["files"]:
        if f["name"].endswith(".deb"):
            debs.append(os.path.join(build_dir, f["name"]))

    with docker(chroot_name) as chroot:
        if extra_repo is not None:
            name = "/etc/apt/sources.list.d/extra_repo.list"
            with chroot.create_file(name, user="root") as f:
                data = "%s\n" % (extra_repo)
                f.write(data.encode("ASCII"))

        chroot.check_call(["apt-get", "update", "--yes"], root=True)
        chroot.check_call(["apt-get", "upgrade", "--yes"], root=True)
        chroot.check_call(["dpkg", "--unpack", "--"] + debs, root=True)
        chroot.check_call(
            ["apt-get", "--yes", "-f", "-oDpkg::Options::=--force-confold", "install"],
            root=True,
        )

        if test_mode == "auto":
            pass
        elif test_mode == "manual":
            chroot.check_call(["bash"], cwd=build_dir, root=True)
        else:
            raise RuntimeError("Unknown test mode %s" % test_mode)


def deb_test_source_only(changes_file: str, test_mode: str) -> None:
    if test_mode == "none":
        return

    build_dir = os.path.dirname(changes_file)

    if test_mode == "auto":
        pass
    elif test_mode in ["manual", "manual_no_unpack"]:
        with chdir(build_dir):
            check_call(["bash"])
    else:
        raise RuntimeError("Unknown test mode %s" % test_mode)


def deb_upload(server: str, delayed: int, changes_file: str, chroot_name: str) -> None:
    with open(changes_file) as f:
        changes = deb822.Changes(f)

    unparsed = changes.get_as_string("Changes")
    parsed = []
    for line in unparsed.split("\n"):
        if line == "":
            continue
        elif line == " .":
            line = ""
        elif line[0] == " ":
            line = line[1:]
        else:
            assert False
        parsed.append(line)

    top_match = changelog.topline.match(parsed[0])
    assert top_match is not None
    distributions = top_match.group(3).lstrip()

    assert distributions == changes["Distribution"]
    assert distributions != "UNRELEASED"

    with docker(chroot_name) as chroot:
        if delayed > 0:
            chroot.check_call(["dput", "--delayed=%d" % delayed, server, changes_file])
        else:
            chroot.check_call(["dput", server, changes_file])


@contextmanager
def temp_dir() -> Iterator[str]:
    tmp_dir = tempfile.mkdtemp()
    cur_dir = os.getcwd()
    try:
        yield tmp_dir
    finally:
        os.chdir(cur_dir)
        shutil.rmtree(tmp_dir)


@contextmanager
def chdir(directory: str) -> Iterator[str]:
    old_dir = os.getcwd()
    try:
        os.chdir(directory)
        yield old_dir
    finally:
        os.chdir(old_dir)


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Build Debian packages with sbuild.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dsc", dest="dsc_path", help="Act on dsc file.")
    group.add_argument(
        "--working", dest="working_dir", help="Act on tree in working directory."
    )

    parser.add_argument(
        "--upload", action="store_true", default=False, help="upload result"
    )

    parser.add_argument(
        "--distros",
        choices=["debian", "linuxpenguins"],
        action="append",
        default=[],
        help="build distros",
    )

    parser.add_argument(
        "--distributions",
        choices=[
            "bullseye",
            "bullseye-security",
            "bookworm",
            "bookworm-security",
            "sid",
            "oldstable",
            "stable",
            "experimental",
        ],
        action="append",
        default=[],
        help="build distributions",
    )

    parser.add_argument(
        "--architectures",
        choices=["i386", "amd64"],
        action="append",
        default=[],
        help="build architecture",
    )

    parser.add_argument(
        "--delayed",
        choices=range(0, 15 + 1),
        default=0,
        type=int,
        help="Upload to a DELAYED queue, rather than the usual Incoming. "
        "This takes an argument from 0 to 15. Note  that  a "
        "delay of 0 is different from no delay at all.",
    )

    parser.add_argument(
        "--test",
        choices=["none", "auto", "manual", "manual_no_unpack"],
        default="auto",
        help="how to test?",
    )

    args = parser.parse_args()

    if args.working_dir:
        dsc_path = deb_build_src(args.working_dir, "brianmay/debian-amd64:sid")
    else:
        dsc_path = args.dsc_path

    distros = set(args.distros)
    if len(distros) == 0:
        distros.add("debian")

    distributions = set(args.distributions)
    if len(distributions) == 0:
        if "debian" in distros:
            distributions.add("sid")

    architectures = list(args.architectures)
    if len(architectures) == 0:
        architectures = ["i386", "amd64"]

    if "debian" in distros:
        build = []
        source_upload = True
        if "bullseye" in distributions:
            build.append("bullseye")
            if args.upload:
                raise RuntimeError("Cannot upload to bullseye")
        if "bullseye-security" in distributions:
            source_upload = False
            build.append("bullseye-security")
        if "bookworm" in distributions:
            build.append("bookworm")
            if args.upload:
                raise RuntimeError("Cannot upload to bookworm")
        if "bookworm-security" in distributions:
            source_upload = False
            build.append("bookworm-security")
        if "oldstable" in distributions:
            build.append("oldstable")
            source_upload = False
        if "stable" in distributions:
            build.append("stable")
            source_upload = False
        if "sid" in distributions:
            build.append("sid")
        if "experimental" in distributions:
            build.append("experimental")

        source = True
        for distribution in build:
            arch_all = True

            real_distribution = distribution
            upload_distribution = distribution

            if distribution == "sid":
                upload_distribution = "unstable"

            if distribution == "oldstable":
                real_distribution = "bullseye"
                upload_distribution = "oldstable"

            if distribution == "stable":
                real_distribution = "bookworm"
                upload_distribution = "stable"

            split = distribution.split("-")
            server = "ftp-master"
            if split[-1] == "security":
                server = "security-master"

            with temp_dir() as tmp_dir:
                tmp_dsc_path = deb_copy_source(tmp_dir, dsc_path)
                for architecture in architectures:
                    build_chroot = f"brianmay/debian-{architecture}:{real_distribution}"
                    test_chroot = f"brianmay/debian-{architecture}:{real_distribution}"
                    changes_file = deb_build(
                        tmp_dir,
                        tmp_dsc_path,
                        build_chroot,
                        upload_distribution,
                        architecture,
                        True,
                        arch_all,
                        source,
                        None,
                    )
                    if changes_file is not None:
                        deb_sign(changes_file, build_chroot)
                        if distribution in ["sid", "experimental"]:
                            deb_lint(changes_file, test_chroot)
                        deb_test(changes_file, test_chroot, args.test, None)
                        if not source_upload and args.upload and source:
                            deb_upload(server, args.delayed, changes_file, build_chroot)
                    arch_all = False
                    source = False

                if source_upload:
                    build_chroot = f"brianmay/debian-source:{real_distribution}"
                    test_chroot = f"brianmay/debian-source:{real_distribution}"
                    changes_file = deb_build(
                        tmp_dir,
                        tmp_dsc_path,
                        build_chroot,
                        upload_distribution,
                        "source",
                        False,
                        False,
                        True,
                        None,
                    )
                    if changes_file is not None:
                        deb_sign(changes_file, build_chroot)
                        deb_test_source_only(changes_file, args.test)
                        if args.upload:
                            deb_upload(server, args.delayed, changes_file, build_chroot)

    # end if 'debian' in distros:


if __name__ == "__main__":
    main()
