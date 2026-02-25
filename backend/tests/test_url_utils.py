"""URL 工具测试"""
import importlib.util
import os
import unittest

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
MODULE_PATH = os.path.join(BACKEND_DIR, "app", "utils", "url.py")

spec = importlib.util.spec_from_file_location("url_utils", MODULE_PATH)
url_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(url_utils)
is_https_url = url_utils.is_https_url


class TestUrlUtils(unittest.TestCase):
    def test_https_url(self):
        self.assertTrue(is_https_url("https://t.me/example"))

    def test_http_url(self):
        self.assertFalse(is_https_url("http://example.com"))

    def test_empty_url(self):
        self.assertFalse(is_https_url(""))

    def test_none_url(self):
        self.assertFalse(is_https_url(None))


if __name__ == "__main__":
    unittest.main()
