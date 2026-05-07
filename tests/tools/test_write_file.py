import sys
import os
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, _project_root)

import unittest
import tempfile
import json

from internal.context.context import Context
from internal.tools.write_file import WritefileTool


class TestWritefileTool(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tool = WritefileTool(work_dir=self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_init(self):
        self.assertEqual(self.tool.name, "write_file")
        self.assertEqual(self.tool.definition.name, "write_file")
        self.assertIn("path", self.tool.definition.input_schema["required"])
        self.assertIn("content", self.tool.definition.input_schema["required"])
        self.assertEqual(self.tool.work_dir, self.tmpdir.name)

    def test_write_new_file(self):
        args = json.dumps({"path": "hello.txt", "content": "Hello, world!"})
        result = self.tool.execute(Context(), args)
        self.assertIn("写入成功", result)

        full_path = os.path.join(self.tmpdir.name, "hello.txt")
        self.assertTrue(os.path.isfile(full_path))
        with open(full_path, "r") as f:
            self.assertEqual(f.read(), "Hello, world!")

    def test_overwrite_existing_file(self):
        full_path = os.path.join(self.tmpdir.name, "existing.txt")
        with open(full_path, "w") as f:
            f.write("old content")

        args = json.dumps({"path": "existing.txt", "content": "new content"})
        result = self.tool.execute(Context(), args)
        self.assertIn("写入成功", result)

        with open(full_path, "r") as f:
            self.assertEqual(f.read(), "new content")

    def test_write_in_nested_directory(self):
        args = json.dumps({"path": "a/b/c/deep.txt", "content": "deep content"})
        result = self.tool.execute(Context(), args)
        self.assertIn("写入成功", result)

        full_path = os.path.join(self.tmpdir.name, "a/b/c/deep.txt")
        self.assertTrue(os.path.isfile(full_path))
        with open(full_path, "r") as f:
            self.assertEqual(f.read(), "deep content")

    def test_write_empty_content(self):
        args = json.dumps({"path": "empty.txt", "content": ""})
        result = self.tool.execute(Context(), args)
        self.assertIn("写入成功", result)

        full_path = os.path.join(self.tmpdir.name, "empty.txt")
        self.assertTrue(os.path.isfile(full_path))
        with open(full_path, "r") as f:
            self.assertEqual(f.read(), "")

    def test_missing_path_key(self):
        with self.assertRaises(KeyError):
            self.tool.execute(Context(), json.dumps({"content": "no path"}))

    def test_missing_content_key(self):
        result = self.tool.execute(Context(), json.dumps({"path": "no_content.txt"}))
        self.assertIn("Error:", result)

    def test_write_failure_readonly_dir(self):
        readonly_dir = os.path.join(self.tmpdir.name, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)

        args = json.dumps({"path": "readonly/fail.txt", "content": "should fail"})
        result = self.tool.execute(Context(), args)
        self.assertIn("Error:", result)

    def test_write_unicode_content(self):
        args = json.dumps({"path": "unicode.txt", "content": "你好，世界！🌍"})
        result = self.tool.execute(Context(), args)
        self.assertIn("写入成功", result)

        full_path = os.path.join(self.tmpdir.name, "unicode.txt")
        with open(full_path, "r") as f:
            self.assertEqual(f.read(), "你好，世界！🌍")


if __name__ == "__main__":
    unittest.main()
