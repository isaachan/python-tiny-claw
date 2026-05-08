import sys
import os
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, _project_root)

import json
import tempfile

import pytest

from internal.context.context import Context
from internal.tools.edit_file import EditfileTool, _normalize_newlines, _min_indent, _strip_indents, _add_indent, _fuzzy_replace


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
    with open(full_path, "w", newline="") as f:
        f.write(content)


def _read_file(work_dir, path):
    full_path = os.path.join(work_dir, path)
    with open(full_path, "r", newline="") as f:
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


# -- old/new text with newlines --
def test_old_text_contains_newline(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    pass\n    return 1\n")
    result = _execute(tool, "code.py", "    pass\n    return 1", "    return 42")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def foo():\n    return 42\n"


def test_new_text_contains_newline(tool, work_dir):
    _write_file(work_dir, "config.ini", "[db]\nhost = localhost\n")
    result = _execute(tool, "config.ini", "[db]", "[database]\nengine = pg")
    assert "替换成功" in result
    assert _read_file(work_dir, "config.ini") == "[database]\nengine = pg\nhost = localhost\n"


def test_both_old_and_new_contain_newlines(tool, work_dir):
    _write_file(work_dir, "poem.txt", "roses are red\nviolets are blue\nsugar is sweet\n")
    result = _execute(tool, "poem.txt", "roses are red\nviolets are blue", "tulips are yellow\ndaisies are white")
    assert "替换成功" in result
    assert _read_file(work_dir, "poem.txt") == "tulips are yellow\ndaisies are white\nsugar is sweet\n"


def test_multi_line_unique_match(tool, work_dir):
    _write_file(work_dir, "api.py", "# TODO: refactor\n# TODO: optimize\n# FIXME: critical bug\n")
    result = _execute(tool, "api.py", "# TODO: optimize", "# DONE: optimized")
    assert "替换成功" in result
    content = _read_file(work_dir, "api.py")
    assert "# DONE: optimized" in content
    assert "# TODO: refactor" in content


def test_multi_line_old_text_repeated(tool, work_dir):
    _write_file(work_dir, "items.py", "class ItemA:\n    pass\n\nclass ItemB:\n    pass\n")
    result = _execute(tool, "items.py", "class", "def")
    assert "出现了 2 次" in result


# -- newline normalization (\r\n vs \n) --
def test_file_crlf_old_text_lf(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\r\n    pass\r\n")
    result = _execute(tool, "code.py", "def foo():\n    pass", "def bar():\n    return 1")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def bar():\r\n    return 1\r\n"


def test_file_lf_old_text_crlf(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    pass\n")
    result = _execute(tool, "code.py", "def foo():\r\n    pass", "def bar():\r\n    return 1")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def bar():\n    return 1\n"


def test_file_crlf_new_text_lf_preserves_crlf(tool, work_dir):
    _write_file(work_dir, "cfg.ini", "[app]\r\nname=foo\r\n")
    result = _execute(tool, "cfg.ini", "[app]\r\nname=foo", "[app]\nname=bar")
    assert "替换成功" in result
    assert _read_file(work_dir, "cfg.ini") == "[app]\r\nname=bar\r\n"


def test_file_lf_new_text_crlf_preserves_lf(tool, work_dir):
    _write_file(work_dir, "cfg.ini", "[app]\nname=foo\n")
    result = _execute(tool, "cfg.ini", "[app]\nname=foo", "[app]\r\nname=bar")
    assert "替换成功" in result
    assert _read_file(work_dir, "cfg.ini") == "[app]\nname=bar\n"


# -- _normalize_newlines unit tests --
def test_normalize_crlf_to_lf():
    assert _normalize_newlines("hello\r\nworld", "\n") == "hello\nworld"


def test_normalize_lf_to_crlf():
    assert _normalize_newlines("hello\nworld", "\r\n") == "hello\r\nworld"


def test_normalize_crlf_to_crlf():
    assert _normalize_newlines("hello\r\nworld", "\r\n") == "hello\r\nworld"


def test_normalize_lf_to_lf():
    assert _normalize_newlines("hello\nworld", "\n") == "hello\nworld"


def test_normalize_mixed_newlines():
    assert _normalize_newlines("line1\r\nline2\nline3", "\n") == "line1\nline2\nline3"


def test_normalize_no_newlines():
    assert _normalize_newlines("hello world", "\r\n") == "hello world"


# -- fuzzy indentation-insensitive matching --
def test_fuzzy_unindented_old_text(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    x=1\n    y=2\n    return x+y\n")
    result = _execute(tool, "code.py", "x=1\ny=2", "x=3\ny=5")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def foo():\n    x=3\n    y=5\n    return x+y\n"


def test_fuzzy_over_indented_old_text(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    x=1\n    y=2\n    return x+y\n")
    result = _execute(tool, "code.py", "        x=1\n        y=2", "x=3\ny=5")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def foo():\n    x=3\n    y=5\n    return x+y\n"


def test_fuzzy_new_text_gets_file_indent(tool, work_dir):
    _write_file(work_dir, "code.py", "if True:\n  a=1\n  b=2\n")
    result = _execute(tool, "code.py", "a=1\nb=2", "a=10\nb=20")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "if True:\n  a=10\n  b=20\n"


def test_fuzzy_preserves_relative_indentation(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    for x in xs:\n        process(x)\n        log(x)\n")
    result = _execute(tool, "code.py", "for x in xs:\n    process(x)\n    log(x)", "for x in xs:\n    handle(x)\n    trace(x)")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def foo():\n    for x in xs:\n        handle(x)\n        trace(x)\n"


def test_fuzzy_not_found(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    x=1\n    y=2\n")
    result = _execute(tool, "code.py", "z=99\nw=100", "a=1\nb=2")
    assert "未找到" in result


def test_fuzzy_multiple_matches(tool, work_dir):
    _write_file(work_dir, "code.py", "if a:\n    x=1\n    y=2\nif b:\n    x=1\n    y=2\n")
    result = _execute(tool, "code.py", "x=1\ny=2", "x=0\ny=0")
    assert "出现了 2 次" in result


def test_fuzzy_empty_lines_preserved(tool, work_dir):
    _write_file(work_dir, "code.py", "def foo():\n    x=1\n\n    y=2\n")
    result = _execute(tool, "code.py", "x=1\n\ny=2", "a=10\n\nb=20")
    assert "替换成功" in result
    assert _read_file(work_dir, "code.py") == "def foo():\n    a=10\n\n    b=20\n"


# -- _min_indent unit tests --
def test_min_indent_basic():
    assert _min_indent(["    x", "  y", "      z"]) == 2


def test_min_indent_with_empty_lines():
    assert _min_indent(["", "  x", "", "    y"]) == 2


def test_min_indent_all_empty():
    assert _min_indent(["", "", ""]) == 0


# -- _strip_indents unit tests --
def test_strip_indents_basic():
    assert _strip_indents(["    x", "    y", ""], 4) == ["x", "y", ""]


def test_strip_indents_preserves_relative():
    assert _strip_indents(["  parent", "    child"], 2) == ["parent", "  child"]


# -- _add_indent unit tests --
def test_add_indent_basic():
    assert _add_indent(["x", "  y", ""], 4) == ["    x", "      y", ""]


# -- _fuzzy_replace unit tests --
def test_fuzzy_replace_success():
    content = "def foo():\n    x=1\n    y=2\n"
    result, err = _fuzzy_replace(content, "x=1\ny=2", "x=3\ny=5", "\n")
    assert result == "def foo():\n    x=3\n    y=5\n"
    assert err is None


def test_fuzzy_replace_not_found():
    result, err = _fuzzy_replace("a\nb\n", "x\ny", "z\nw", "\n")
    assert result is None
    assert err == 0


def test_fuzzy_replace_multiple():
    content = "if a:\n    x=1\n    y=2\nif b:\n    x=1\n    y=2\n"
    result, err = _fuzzy_replace(content, "x=1\ny=2", "z=1\nw=2", "\n")
    assert result is None
    assert err == 2


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
