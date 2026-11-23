"""Restore public build outputs hidden by the isolated source-workspace mount."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .task_environment import docker, extract_task_archive


PACKAGES = {'astropy/astropy': 'astropy', 'scikit-learn/scikit-learn': 'sklearn'}


def runtime_path(name: str, package: str) -> bool:
    path = Path(name)
    if path.is_absolute() or any(x in {'.git', '..', '__pycache__', 'tests', 'test'} for x in path.parts):
        return False
    if '\n' in name or '\r' in name or not path.parts:
        return False
    if path.parts[0].endswith('.egg-info'):
        return len(path.parts) > 1
    return path.parts[0] == package and (
        re.search(r'\.so(?:\.|$)', path.name) is not None or path.suffix in {'.pyd', '.dylib'}
        or path.name in {'version.py', '_version.py'}
    )


def restore_runtime_files(container: str, repo: str, workspace: Path) -> dict:
    package = PACKAGES.get(repo)
    if package is None:
        return {}
    names = set()
    for extra in ([], ['--ignored']):
        listing = docker('exec', '-w', '/testbed', container, 'git', 'ls-files',
                         '--others', '--exclude-standard', '-z', *extra).stdout
        names.update(n for n in listing.split('\0') if n and runtime_path(n, package))
    if not names:
        raise ValueError(f'No runtime files found in compiled task image: {repo}')
    # The source is the verified original instance image, never a grader container.
    data = subprocess.check_output(
        ['docker', 'exec', '-i', '-w', '/testbed', container, 'tar', '--hard-dereference',
         '-cf', '-', '--null', '-T', '-'], input=('\0'.join(sorted(names))+'\0').encode(), timeout=120)
    hashes = {}
    with tempfile.TemporaryDirectory(prefix='hecate-runtime-') as tmp:
        stage = Path(tmp)/'files'
        extract_task_archive(data, stage)
        for name in sorted(names):
            source, target = stage/name, workspace/name
            if target.exists() or target.is_symlink():
                raise ValueError(f'Runtime file collides with original source: {name}')
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                target.symlink_to(source.readlink())
            else:
                shutil.copy2(source, target)
            hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    # Keep public generated files out of candidate source patches. Git metadata
    # is read-only inside AgentSandbox; the model cannot change these patterns.
    exclude = workspace/'.git/info/exclude'
    with exclude.open('a') as stream:
        for name in sorted(names):
            stream.write('/'+re.sub(r'([\\*?\[\]#! ])', r'\\\1', name)+'\n')
    return hashes
