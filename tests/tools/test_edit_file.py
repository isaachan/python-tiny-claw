import sys
import os
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, _project_root)

import json
import tempfile

import pytest

from internal.context.context import Context
from internal.tools.edit_file import EditfileTool


@pytest.fixture
def tool():
    tmpdir = tempfile.TemporaryDirectory()
    yield EditfileTool(work_dir=tmpdir.name)
    tmpdir.cleanup()


@pytest.fixture
def work_dir(tool):
    return tool.work_dir


def _write_file(work_dir, path, content):
    full_path = os.path.join(work_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)


def _read_file(work_dir, path):
    full_path = os.path.join(work_dir, path)
    with open(full_path, "r") as f:
        return f.read()


def _execute(tool, path, old_text, new_text):
    args = json.dumps({"path": path, "old_text": old_text, "new_text": new_text})
    return tool.execute(Context(), args)


# -- init --
def test_init(tool):
    assert tool.name == "edit_file"
    assert tool.definition.name == "edit_file"
    assert "path" in tool.definition.input_schema["required"]
    assert "old_text" in tool.definition.input_schema["required"]
    assert "new_text" in tool.definition.input_schema["required"]


# -- successful replacement --
def test_replace_single_word(tool, work_dir):
    _write_file(work_dir, "hello.py", "print('hello world')")
    result = _execute(tool, "hello.py", "hello", "goodbye")
    assert "替换成功" in result
    assert _read_file(work_dir, "hello.py") == "print('goodbye world')"


def test_replace_full_sentence(tool, work_dir):
    _write_file(work_dir, "config.yaml", "database:\n  host: localhost\n  port: 5432\n")
    result = _execute(tool, "config.yaml", "host: localhost", "host: db.example.com")
    assert "替换成功" in result
    content = _read_file(work_dir, "config.yaml")
    assert "host: db.example.com" in content
    assert "host: localhost" not in content


def test_replace_with_empty_string(tool, work_dir):
    _write_file(work_dir, "data.txt", "remove_me and keep_me")
    result = _execute(tool, "data.txt", "remove_me ", "")
    assert "替换成功" in result
    assert _read_file(work_dir, "data.txt") == "and keep_me"


def test_replace_unicode(tool, work_dir):
    _write_file(work_dir, "i18n.py", "greeting = '你好世界'")
    result = _execute(tool, "i18n.py", "你好世界", "こんにちは")
    assert "替换成功" in result
    assert _read_file(work_dir, "i18n.py") == "greeting = 'こんにちは'"


def test_replace_in_nested_path(tool, work_dir):
    _write_file(work_dir, "src/lib/utils.py", "VERSION = '1.0.0'")
    result = _execute(tool, "src/lib/utils.py", "1.0.0", "2.0.0")
    assert "替换成功" in result
    assert _read_file(work_dir, "src/lib/utils.py") == "VERSION = '2.0.0'"


# -- old/new text with surrounding whitespace --
def test_old_text_with_leading_spaces(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    pass\n")
    result = _execute(tool, "code.py", "    pass", "    return 42")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def foo():\n    return 42\n"


def test_old_text_with_trailing_spaces(tool, work_dir):
    _write_file(work_dir, "data.txt", "hello   world")
    result = _execute(tool, "data.txt", "hello   ", "hi ")
    assert "替换成功" in result
    assert _read_file(work_dir, "data.txt") == "hi world"


def test_new_text_with_leading_and_trailing_spaces(tool, work_dir):
    _write_file(work_dir, "cfg.ini", "name=admin")
    result = _execute(tool, "cfg.ini", "=", " = ")
    assert "替换成功" in result
    assert _read_file(work_dir, "cfg.ini") == "name = admin"


def test_old_text_has_trailing_newline_not_matched(tool, work_dir):
    _write_file(work_dir, "f.py", "x = 1\n")
    result = _execute(tool, "f.py", "x = 1", "x = 2")
    assert "替换成功" in result
    assert _read_file(work_dir, "f.py") == "x = 2\n"


def test_whitespace_only_old_text(tool, work_dir):
    _write_file(work_dir, "spaces.txt", "a     b")
    result = _execute(tool, "spaces.txt", "     ", " :: ")
    assert "替换成功" in result
    assert _read_file(work_dir, "spaces.txt") == "a :: b"


# -- file not found --
def test_file_not_found(tool, work_dir):
    result = _execute(tool, "nonexistent.txt", "foo", "bar")
    assert "不存在" in result


# -- old_text not found --
def test_old_text_not_found(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    pass\n")
    result = _execute(tool, "code.py", "bar", "baz")
    assert "未找到" in result


# -- multiple matches --
def test_old_text_appears_multiple_times(tool, work_dir):
    _write_file(work_dir, "dupes.txt", "x = 1\ny = 1\nz = 1\n")
    result = _execute(tool, "dupes.txt", "1", "42")
    assert "出现了 3 次" in result


def test_unique_match_with_repeated_context(tool, work_dir):
    _write_file(work_dir, "code.py", "import os\n\n# os is used here\nos.getcwd()\n")
    result = _execute(tool, "code.py", "# os is used here", "# os is used everywhere")
    assert "替换成功" in result
    content = _read_file(work_dir, "code.py")
    assert "os is used everywhere" in content


# -- missing required arguments --
def test_missing_path_key(tool):
    with pytest.raises(KeyError):
        tool.execute(Context(), json.dumps({"old_text": "a", "new_text": "b"}))


def test_missing_old_text_key(tool, work_dir):
    _write_file(work_dir, "f.txt", "hello")
    with pytest.raises(KeyError):
        tool.execute(Context(), json.dumps({"path": "f.txt", "new_text": "b"}))


def test_missing_new_text_key(tool, work_dir):
    _write_file(work_dir, "f.txt", "hello")
    with pytest.raises(KeyError):
        tool.execute(Context(), json.dumps({"path": "f.txt", "old_text": "a"}))
