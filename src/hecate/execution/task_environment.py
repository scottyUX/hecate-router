"""Disposable Docker task trees and separate no-network Tenacity grading.

No Docker socket, host home, evaluator metadata, or source git history enters the
agent. The Unix inference socket is the sole host service available to it.
"""

from __future__ import annotations
import io
import json
import os
import posixpath
import re
import subprocess
import time
import tarfile
import tempfile
import uuid
from pathlib import Path


def docker(
    *args: str, timeout: int = 120, check: bool = True, input: str | None = None
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["docker", *args], input=input, capture_output=True, text=True, timeout=timeout
    )
    if check and result.returncode:
        raise RuntimeError(f"Docker {args[0]} failed: {result.stderr[-1000:]}")
    return result


def validate_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError("Invalid instance ID")
    return value


def protected_test_path(path: str) -> bool:
    parts = Path(path).parts
    return (
        any(p in {"test", "tests", "testing"} for p in parts)
        or Path(path).name.startswith("test_")
        or Path(path).name
        in {"conftest.py", "pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"}
    )


def extract_task_archive(data: bytes, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        members = {m.name: m for m in archive.getmembers()}
        links = []
        for member in members.values():
            p = Path(member.name)
            if (
                p.is_absolute()
                or ".." in p.parts
                or ".git" in p.parts
                or member.islnk()
            ):
                raise ValueError(f"Unsafe task archive entry: {member.name}")
            if member.issym():
                destination = posixpath.normpath(str(p.parent / member.linkname))
                if (
                    Path(member.linkname).is_absolute()
                    or destination not in members
                    or not members[destination].isfile()
                ):
                    raise ValueError(f"Unsafe task symlink: {member.name}")
                links.append(member)
            elif not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsupported task archive type: {member.name}")
        # Extract no links until regular content is in place; only contained
        # links directly to an archived regular file are permitted.
        archive.extractall(
            target, members=[m for m in members.values() if not m.issym()]
        )
        for member in links:
            (target / member.name).symlink_to(member.linkname)


def export_task_tree(image: str, instance_id: str, target: Path) -> str:
    """Export selected tracked files only; create a fresh single-commit git repo."""
    validate_id(instance_id)
    name = "task001-prep-" + uuid.uuid4().hex[:10]
    docker("run", "-d", "--name", name, "--network", "none", image, "sleep", "600")
    try:
        docker("exec", "-w", "/testbed", name, "git", "checkout", instance_id)
        revision = docker(
            "exec", "-w", "/testbed", name, "git", "rev-parse", "HEAD"
        ).stdout.strip()
        result = subprocess.run(
            ["docker", "exec", "-w", "/testbed", name, "git", "archive", "HEAD"],
            capture_output=True,
            check=True,
            timeout=120,
        )
        extract_task_archive(result.stdout, target)
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "-c",
                "user.name=Hecate fixture",
                "-c",
                "user.email=fixture@localhost",
                "commit",
                "-qm",
                "Isolated task base",
            ],
            check=True,
        )
        return revision
    finally:
        docker("rm", "-f", name, check=False)


class AgentSandbox:
    def __init__(
        self, image: str, workspace: Path, tools: Path, config: Path, socket_dir: Path
    ):
        self.name = "task001-agent-" + uuid.uuid4().hex[:10]
        self.image, self.workspace, self.tools, self.config, self.socket_dir = (
            image,
            workspace,
            tools,
            config,
            socket_dir,
        )

    def __enter__(self):
        relay = Path(__file__).with_name("codex_relay.py").resolve()
        immutable = ["-v", f"{self.workspace.resolve()}/.git:/testbed/.git:ro"]
        for path in self.workspace.rglob("*"):
            relative = path.relative_to(self.workspace)
            if (
                ".git" in relative.parts
                or not path.is_file()
                or not protected_test_path(str(relative))
            ):
                continue
            immutable.extend(["-v", f"{path.resolve()}:/testbed/{relative}:ro"])
        docker(
            "run",
            "-d",
            "--name",
            self.name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--memory",
            "8g",
            "--cpus",
            "4",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--tmpfs",
            "/tmp:rw,exec,size=512m,mode=1777",
            "-v",
            f"{self.workspace.resolve()}:/testbed:rw",
            "-v",
            f"{self.tools.resolve()}:/opt/codex:ro",
            "-v",
            f"{self.config.resolve()}:/opt/hecate-config:ro",
            "-v",
            f"{self.socket_dir.resolve()}:/opt/hecate-socket:ro",
            "-v",
            f"{relay}:/opt/hecate-relay.py:ro",
            "-w",
            "/testbed",
            "-e",
            "HOME=/tmp/home",
            "-e",
            "CODEX_HOME=/tmp/home/.codex",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "PATH=/opt/codex/bin:/opt/codex/codex-path:/opt/miniconda3/envs/testbed/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            *immutable,
            self.image,
            "bash",
            "-lc",
            "mkdir -p /tmp/home/.codex && cp /opt/hecate-config/config.toml /tmp/home/.codex/config.toml && exec /opt/miniconda3/envs/testbed/bin/python /opt/hecate-relay.py /opt/hecate-socket/gateway.sock 8127",
        )
        try:
            for _ in range(30):
                probe = docker(
                    "exec",
                    self.name,
                    "/opt/miniconda3/envs/testbed/bin/python",
                    "-c",
                    "import socket; s=socket.create_connection(('127.0.0.1',8127),timeout=1);s.close()",
                    timeout=5,
                    check=False,
                )
                if probe.returncode == 0:
                    return self
                inspection = json.loads(docker("inspect", self.name).stdout)[0]
                if not inspection["State"]["Running"]:
                    break
                time.sleep(0.1)
            logs = docker("logs", self.name, check=False)
            raise RuntimeError(
                "Agent relay failed to start: "
                + logs.stdout[-1500:]
                + logs.stderr[-1500:]
            )
        except BaseException:
            docker("rm", "-f", self.name, check=False)
            raise

    def command(self, prompt: str) -> list[str]:
        return [
            "docker",
            "exec",
            self.name,
            "/opt/codex/bin/codex",
            "exec",
            "--json",
            "--strict-config",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            prompt,
        ]

    def __exit__(self, *args):
        docker("rm", "-f", self.name, check=False)


def changed_files(workspace: Path) -> list[str]:
    out = subprocess.check_output(
        ["git", "-C", str(workspace), "status", "--porcelain", "-z"], text=True
    )
    return [line[3:] for line in out.split("\0") if line]


def collect_patch(workspace: Path, base_commit: str = "HEAD") -> tuple[str, list[str]]:
    # Include new files and compare to the externally recorded original base,
    # even when an agent has made its own commits.
    subprocess.run(
        ["git", "-C", str(workspace), "add", "--intent-to-add", "."], check=True
    )
    files = subprocess.check_output(
        ["git", "-C", str(workspace), "diff", "--name-only", base_commit], text=True
    ).splitlines()
    rejected = [p for p in files if protected_test_path(p)]
    return _binary_diff(workspace, base_commit, files), rejected


def _binary_diff(workspace: Path, base_commit: str, files: list[str]) -> str:
    """Files git sniffs as text but that are not UTF-8 (no NUL byte, e.g. a Sphinx
    objects.inv: text header, zlib body) are marked binary so --binary encodes
    them losslessly in ASCII instead of failing the attempt."""
    command = ["git", "-C", str(workspace), "diff", "--binary", base_commit]
    try:
        return subprocess.check_output(command).decode()
    except UnicodeDecodeError:
        pass
    undecodable = []
    for path in files:
        try:
            subprocess.check_output(command + ["--", path]).decode()
        except UnicodeDecodeError:
            undecodable.append(path)
    with tempfile.NamedTemporaryFile("w", suffix=".gitattributes") as attributes:
        for path in undecodable:
            pattern = re.sub(r"([\\*?\[\]!#])", r"\\\1", path).replace(" ", "[[:space:]]")
            attributes.write(f"/{pattern} binary\n")
        attributes.flush()
        command[3:3] = ["-c", f"core.attributesFile={attributes.name}"]
        return subprocess.check_output(command).decode()


TEST_LINE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")


def grade_patch(
    image: str,
    instance: dict,
    patch: str,
    output: Path,
    *,
    gold: bool = False,
    validated_controls: bool = False,
    verified_gold: bool = False,
) -> dict:
    """Evaluator-only history restores hidden tests. Gold reverses injected bug."""
    name = "task001-grade-" + uuid.uuid4().hex[:10]
    validate_id(instance["instance_id"])
    output.mkdir(parents=True, exist_ok=False)
    docker(
        "run",
        "-d",
        "--name",
        name,
        "--network",
        "none",
        "--pids-limit",
        "256",
        "--memory",
        "8g",
        image,
        "sleep",
        "1200",
    )
    try:
        docker(
            "exec",
            "-w",
            "/testbed",
            name,
            "git",
            "checkout",
            instance["instance_id"],
        )
        # Pin the restored path list instead of interpolating it into a shell.
        paths = docker(
            "exec",
            "-w",
            "/testbed",
            name,
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "HEAD~1",
        ).stdout.splitlines()
        if any(not protected_test_path(p) for p in paths):
            raise ValueError("Hidden-test restoration changes non-test files")
        if paths:
            docker(
                "exec",
                "-w",
                "/testbed",
                name,
                "git",
                "checkout",
                "HEAD~1",
                "--",
                *paths,
            )
        if gold:
            docker(
                "exec",
                "-i",
                "-w",
                "/testbed",
                name,
                "git",
                "apply",
                "-R",
                "-",
                input=instance["patch"],
            )
        elif patch:
            docker(
                "exec", "-i", "-w", "/testbed", name, "git", "apply", "-", input=patch
            )
        result = docker(
            "exec",
            "-w",
            "/testbed",
            name,
            "/opt/miniconda3/envs/testbed/bin/python",
            "-m",
            "pytest",
            "--disable-warnings",
            "--color=no",
            "--tb=short",
            "--verbose",
            timeout=900,
            check=False,
        )
        log = result.stdout + "\n" + result.stderr
        (output / "pytest.log").write_text(log)
        statuses = {
            m.group(1): m.group(2)
            for line in log.splitlines()
            if (m := TEST_LINE.match(line.strip()))
        }
        f2p = instance["FAIL_TO_PASS"]
        p2p = instance["PASS_TO_PASS"]
        if isinstance(f2p, str):
            f2p = json.loads(f2p)
        if isinstance(p2p, str):
            p2p = json.loads(p2p)
        bug_collection_failure = verified_gold and not gold and not patch and not p2p
        if (
            ((validated_controls and patch) or bug_collection_failure)
            and result.returncode == 2
            and re.search(r"\b[1-9]\d* errors? during collection\b", log)
        ):
            outcome = {
                "status": "completed",
                "resolved": False,
                "reason": (
                    "unpatched_bug_broke_test_collection"
                    if bug_collection_failure
                    else "patch_broke_test_collection"
                ),
                "exit_code": result.returncode,
                "f2p": {t: statuses.get(t) for t in f2p},
                "p2p": {t: statuses.get(t) for t in p2p},
            }
        else:
            if (
                not f2p
                or any(t not in statuses for t in f2p + p2p)
                or result.returncode not in (0, 1)
            ):
                raise RuntimeError(
                    "Evaluator did not produce every required test outcome"
                )
            outcome = {
                "status": "completed",
                "resolved": all(statuses[t] == "PASSED" for t in f2p + p2p),
                "f2p": {t: statuses[t] for t in f2p},
                "p2p": {t: statuses[t] for t in p2p},
                "exit_code": result.returncode,
            }
    except (RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        outcome = {"status": "evaluator_failure", "resolved": None, "error": str(exc)}
    finally:
        docker("rm", "-f", name, check=False)
    (output / "outcome.json").write_text(json.dumps(outcome, indent=2) + "\n")
    return outcome
