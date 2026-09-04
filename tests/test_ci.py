"""Tests for the preventive CI pipeline (annotations + hook install)."""
import subprocess
import textwrap
from pathlib import Path

from codegate.ci import _annotation, changed_python_files, run_ci


def test_annotation_format():
    a = _annotation("error", "a.py", 4, "CodeGate: leak", "msg with % and\nnewline")
    assert a.startswith("::error file=a.py,line=4,title=")
    assert "%25" in a
    assert "%0A" in a
    assert "\n" not in a.split("::", 2)[2]


def test_run_ci_exit_codes(tmp_path):
    leaky = tmp_path / "leaky.py"
    leaky.write_text(textwrap.dedent("""
    def leak(p):
        f = open(p)
        return f.read()
    """))
    rc = run_ci([str(leaky)], quiet=True)
    assert rc == 1

    clean = tmp_path / "clean.py"
    clean.write_text(textwrap.dedent("""
    def ok(p):
        with open(p) as f:
            return f.read()
    """))
    rc = run_ci([str(clean)], quiet=True)
    assert rc == 0


def test_install_hook_and_block(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=30)
    assert git("init", "-q").returncode == 0
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")

    # install hook from within the repo
    orig_cwd = Path.cwd()
    try:
        import os
        os.chdir(repo)
        from codegate.ci import install_hook
        assert install_hook() == 0
    finally:
        os.chdir(orig_cwd)

    hook = repo / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    assert "codegate.ci" in hook.read_text()

    # stage a leaky file — the hook should block the commit
    (repo / "leak.py").write_text(textwrap.dedent("""
    def leak(p):
        f = open(p)
        return f.read()
    """))
    git("add", "leak.py")
    # hook needs to import codegate — inject PYTHONPATH of this project
    import sys
    project_root = str(Path(__file__).resolve().parents[1])
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "PYTHONPATH": project_root, "HOME": str(tmp_path)}
    r = subprocess.run(["git", "-C", str(repo), "commit", "-m", "x"],
                       capture_output=True, text=True, timeout=60,
                       env={"PATH": "/usr/bin:/bin", "GIT_AUTHOR_NAME": "t",
                            "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                            "GIT_COMMITTER_EMAIL": "t@t", "PYTHONPATH": project_root,
                            "HOME": str(tmp_path)})
    out = r.stdout + r.stderr
    assert "commit blocked" in out or "FAILED" in out
    log = git("log", "--oneline").stdout
    assert len(log.strip().splitlines()) == 0  # no commits created


def test_changed_python_files_runs():
    # in the actual repo there should be at least some changed file or none —
    # just verify it doesn't crash and returns a list
    files = changed_python_files()
    assert isinstance(files, list)
