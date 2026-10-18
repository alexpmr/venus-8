import unittest
from venus8.updater import version_tuple, is_newer, release_asset


class TestUpdater(unittest.TestCase):
    def test_semver(self):
        self.assertEqual(version_tuple("v0.2.1"),(0,2,1))
        self.assertIsNone(version_tuple("something-else"))
        self.assertTrue(is_newer("v0.2.2","0.2.1"))
        self.assertFalse(is_newer("v0.2.1","0.2.1"))
        self.assertFalse(is_newer("v0.1.0","0.2.1"))

    def test_release_asset_selection(self):
        release={"assets":[
            {"name":"Venus-8-v0.2.1-Windows-Setup.exe"},
            {"name":"Venus-8-v0.2.1-Windows-Portable.exe"},
            {"name":"SHA256SUMS.txt"}]}
        self.assertEqual(release_asset(release,False)["name"],release["assets"][0]["name"])
        self.assertEqual(release_asset(release,True)["name"],release["assets"][1]["name"])
        self.assertIsNone(release_asset({"assets":[]},False))


if __name__=="__main__":
    unittest.main()
