import unittest

from check_coss_state import classify


class TestClassify(unittest.TestCase):
    def test_empty_project_is_init(self):
        self.assertEqual(classify({}), "init")

    def test_app_without_coss_is_init(self):
        markers = {"has_app": True, "has_coss_registry": False,
                   "has_base_ui_dep": False, "has_coss_tokens": False}
        self.assertEqual(classify(markers), "init")

    def test_coss_registry_means_add(self):
        self.assertEqual(classify({"has_coss_registry": True}), "add")

    def test_base_ui_dep_means_add(self):
        self.assertEqual(classify({"has_base_ui_dep": True}), "add")

    def test_coss_tokens_means_add(self):
        self.assertEqual(classify({"has_coss_tokens": True}), "add")

    def test_any_marker_wins(self):
        markers = {"has_app": True, "has_coss_registry": False,
                   "has_base_ui_dep": True, "has_coss_tokens": False}
        self.assertEqual(classify(markers), "add")


if __name__ == "__main__":
    unittest.main()
