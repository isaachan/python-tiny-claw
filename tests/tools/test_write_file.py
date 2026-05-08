import sys
import os
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, _project_root)

import json
import tempfile

import pytest

from internal.context.context import Context
from internal.tools.write_file import WritefileTool


@pytest.fixture
def tool():
    tmpdir = tempfile.TemporaryDirectory()
    yield WritefileTool(work_dir=tmpdir.name)
    tmpdir.cleanup()


@pytest.fixture
def work_dir(tool):
    return tool.work_dir


def execute(tool, path, content):
    return tool.execute(Context(), json.dumps({"path": path, "content": content}))


# -- init / definition --
def test_tool_name_and_definition(tool):
    assert tool.name == "write_file"
    assert tool.definition.name == "write_file"
    assert "path" in tool.definition.input_schema["required"]
    assert "content" in tool.definition.input_schema["required"]


def test_work_dir_is_set(tool, work_dir):
    assert tool.work_dir == work_dir


# -- basic write --
def test_write_new_file(tool, work_dir):
    result = execute(tool, "hello.txt", "Hello, world!")
    assert "写入成功" in result

    full_path = os.path.join(work_dir, "hello.txt")
    assert os.path.isfile(full_path)
    with open(full_path, "r") as f:
        assert f.read() == "Hello, world!"


# -- overwrite --
def test_overwrite_existing_file(tool, work_dir):
    full_path = os.path.join(work_dir, "existing.txt")
    with open(full_path, "w") as f:
        f.write("old content")

    result = execute(tool, "existing.txt", "new content")
    assert "写入成功" in result

    with open(full_path, "r") as f:
        assert f.read() == "new content"


# -- auto-create parent directories --
def test_write_in_nested_directory(tool, work_dir):
    result = execute(tool, "a/b/c/deep.txt", "deep content")
    assert "写入成功" in result

    full_path = os.path.join(work_dir, "a/b/c/deep.txt")
    assert os.path.isfile(full_path)
    with open(full_path, "r") as f:
        assert f.read() == "deep content"


# -- empty content --
def test_write_empty_content(tool, work_dir):
    result = execute(tool, "empty.txt", "")
    assert "写入成功" in result

    full_path = os.path.join(work_dir, "empty.txt")
    assert os.path.isfile(full_path)
    with open(full_path, "r") as f:
        assert f.read() == ""


# -- missing path --
def test_missing_path_key(tool):
    with pytest.raises(KeyError):
        tool.execute(Context(), json.dumps({"content": "no path"}))


# -- missing content (KeyError caught by inner try/except) --
def test_missing_content_key(tool):
    result = tool.execute(Context(), json.dumps({"path": "no_content.txt"}))
    assert "Error:" in result


# -- invalid JSON --
def test_invalid_json_args(tool):
    with pytest.raises(json.JSONDecodeError):
        tool.execute(Context(), "not json")


# -- readonly directory --
def test_write_failure_readonly_dir(tool, work_dir):
    readonly_dir = os.path.join(work_dir, "readonly")
    os.makedirs(readonly_dir)
    os.chmod(readonly_dir, 0o444)

    result = tool.execute(
        Context(),
        json.dumps({"path": "readonly/fail.txt", "content": "should fail"}),
    )
    assert "Error:" in result


# -- unicode content --
def test_write_unicode_content(tool, work_dir):
    result = execute(tool, "unicode.txt", "你好，世界！🌍")
    assert "写入成功" in result

    full_path = os.path.join(work_dir, "unicode.txt")
    with open(full_path, "r") as f:
        assert f.read() == "你好，世界！🌍"


# -- multi-line content --
def test_multiline_content(tool, work_dir):
    content = "line1\nline2\nline3"
    execute(tool, "multi.txt", content)
    with open(os.path.join(work_dir, "multi.txt"), "r") as f:
        assert f.read() == content


# -- path is relative to work_dir --
def test_path_is_relative_to_work_dir(tool, work_dir):
    execute(tool, "data.txt", "data")
    assert os.path.isfile(os.path.join(work_dir, "data.txt"))
