import sys
import os
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, _project_root)

import json
import tempfile

import pytest

from internal.context.context import Context
from internal.tools.bash import BashTool


@pytest.fixture
def tool():
    tmpdir = tempfile.TemporaryDirectory()
    yield BashTool(work_dir=tmpdir.name)
    tmpdir.cleanup()


def execute(tool, command, timeout=None):
    args = {"command": command}
    if timeout is not None:
        args["timeout"] = timeout
    return tool.execute(Context(), json.dumps(args))


@pytest.fixture
def work_dir(tool):
    return tool.work_dir


# -- stdout capture --
def test_command_returns_stdout(tool):
    result = execute(tool, "echo hello world")
    assert "hello world" in result
    assert "[stderr]" not in result
    assert "[exit code" not in result


# -- stderr capture --
def test_command_returns_stderr(tool):
    result = execute(tool, "echo error >&2")
    assert "[stderr]" in result
    assert "error" in result


# -- non-zero exit code --
def test_nonzero_exit_code_reported(tool):
    result = execute(tool, "exit 42")
    assert "[exit code: 42]" in result


# -- empty output + success --
def test_no_output_returns_success_message(tool):
    result = execute(tool, "true")
    assert "Command executed successfully (no output)." in result
    assert "[exit code: 0]" in result


def test_mkdir_no_output_but_actually_creates_dir(tool, work_dir):
    dirname = "newdir"
    result = execute(tool, f"mkdir {dirname}")
    assert "Command executed successfully (no output)." in result
    assert os.path.isdir(os.path.join(work_dir, dirname))


# -- timeout --
def test_timeout_kills_long_command(tool):
    result = execute(tool, "sleep 10", timeout=1)
    assert "timed out" in result


def test_default_timeout_does_not_trigger_normally(tool):
    result = execute(tool, "echo quick")
    assert "timed out" not in result


# -- complex shell syntax --
def test_pipeline(tool):
    result = execute(tool, "echo foo | tr 'a-z' 'A-Z'")
    assert "FOO" in result


def test_chained_and(tool):
    result = execute(tool, "echo one && echo two")
    assert "one" in result
    assert "two" in result


def test_chained_or(tool):
    result = execute(tool, "true || echo nope")
    assert "nope" not in result


def test_environment_variable(tool):
    result = execute(tool, "MYVAR=hello env | grep MYVAR")
    assert "MYVAR=hello" in result


def test_shell_redirect_to_file(tool, work_dir):
    fname = "out.txt"
    execute(tool, f"echo saved > {fname}")
    with open(os.path.join(work_dir, fname), "r") as f:
        assert f.read().strip() == "saved"


# -- working directory binding --
def test_runs_in_work_dir(tool, work_dir):
    execute(tool, "echo cwd > marker.txt")
    assert os.path.isfile(os.path.join(work_dir, "marker.txt"))


def test_does_not_pollute_cwd(tool):
    original_cwd = os.getcwd()
    execute(tool, "echo wherever")
    assert os.getcwd() == original_cwd


# -- combined stdout + stderr + exit code --
def test_stdout_stderr_and_exit_code_all_present(tool):
    result = execute(tool, "echo ok && echo fail >&2 && exit 3")
    assert "ok" in result
    assert "fail" in result
    assert "[stderr]" in result
    assert "[exit code: 3]" in result


# -- output truncation --
def test_large_output_is_truncated(tool):
    result = execute(tool, "python3 -c \"print('x' * 9000)\"")
    assert "[truncated" in result
    assert "more bytes]" in result


def test_short_output_is_not_truncated(tool):
    result = execute(tool, "echo short")
    assert "[truncated" not in result


# -- missing required argument --
def test_missing_command_key(tool):
    with pytest.raises(KeyError):
        tool.execute(Context(), json.dumps({"not_command": "ls"}))
