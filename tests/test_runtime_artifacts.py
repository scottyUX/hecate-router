import io
import subprocess
import tarfile
from pathlib import Path

import pytest
from hecate.execution import runtime_artifacts as runtime
from hecate.execution.task_environment import collect_patch


def archive(files):
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w') as tar:
        for name,data in files.items():
            info=tarfile.TarInfo(name);info.size=len(data)
            tar.addfile(info,io.BytesIO(data))
    return output.getvalue()


def repository(path):
    path.mkdir();(path/'source.py').write_text('value=1\n')
    subprocess.run(['git','init','-q',str(path)],check=True)
    subprocess.run(['git','-C',str(path),'add','.'],check=True)
    subprocess.run(['git','-C',str(path),'-c','user.name=Test','-c','user.email=test@localhost','commit','-qm','Base'],check=True)


def mock_image(monkeypatch,files):
    monkeypatch.setattr(runtime,'docker',lambda *a,**k:subprocess.CompletedProcess(a,0,'\0'.join(files)+'\0',''))
    original=subprocess.check_output
    def command(args,**kwargs):
        return archive(files) if args[0]=='docker' else original(args,**kwargs)
    monkeypatch.setattr(runtime.subprocess,'check_output',command)


def test_restored_runtime_files_never_enter_source_patch(tmp_path,monkeypatch):
    p=tmp_path/'workspace';repository(p)
    files={'astropy/utils/_compiler.cpython-39.so':b'public compiled file',
           'astropy/_version.py':b'__version__="5.0"\n','astropy.egg-info/PKG-INFO':b'Name: astropy'}
    mock_image(monkeypatch,files)
    hashes=runtime.restore_runtime_files('image','astropy/astropy',p)
    assert set(hashes)==set(files)
    assert collect_patch(p)==('',[])
    (p/'source.py').write_text('value=2\n')
    patch,_=collect_patch(p)
    assert 'value=2' in patch and '_compiler' not in patch and 'PKG-INFO' not in patch


def test_runtime_source_collision_fails_closed(tmp_path,monkeypatch):
    p=tmp_path/'workspace';repository(p)
    (p/'astropy').mkdir();(p/'astropy/version.py').write_text('original')
    mock_image(monkeypatch,{'astropy/version.py':b'overwrite'})
    with pytest.raises(ValueError,match='collides'):runtime.restore_runtime_files('image','astropy/astropy',p)
    assert (p/'astropy/version.py').read_text()=='original'


@pytest.mark.parametrize('name',['../bad.so','/bad.so','astropy/tests/bad.so','astropy/__pycache__/x.so','astropy/.git/bad.so','other/evil.so','astropy/source.py','astropy/thing.source.py'])
def test_runtime_filter_rejects_source_and_unsafe_paths(name):
    assert not runtime.runtime_path(name,'astropy')


def test_unsafe_archive_cannot_escape(tmp_path,monkeypatch):
    p=tmp_path/'workspace';repository(p)
    mock_image(monkeypatch,{'astropy/utils/_compiler.so':b'public'})
    original=runtime.subprocess.check_output
    monkeypatch.setattr(runtime.subprocess,'check_output',lambda a,**k:archive({'../escape.so':b'bad'}) if a[0]=='docker' else original(a,**k))
    with pytest.raises(ValueError,match='Unsafe'):runtime.restore_runtime_files('image','astropy/astropy',p)
    assert not (tmp_path/'escape.so').exists()
