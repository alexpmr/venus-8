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



class RelaunchAfterUpdateTests(unittest.TestCase):
    def test_silent_update_reopens_the_app(self):
        # The app runs Setup with /SILENT; a [Run] entry flagged skipifsilent
        # would leave Venus-8 closed after the update.
        import re
        from pathlib import Path
        script = Path("installer/venus8.iss").read_text(encoding="utf-8")
        run = script.split("[Run]", 1)[1]
        launch = [line for line in run.splitlines()
                  if "Venus-8.exe" in line and not line.lstrip().startswith(";")]
        self.assertEqual(len(launch), 1)
        flags = re.search(r"Flags:\s*([^;]+)", launch[0]).group(1).split()
        self.assertIn("postinstall", flags)
        self.assertNotIn("skipifsilent", flags)
        self.assertNotIn("runascurrentuser", flags)

    def test_installer_runs_silently_and_closes_the_old_app(self):
        from unittest import mock
        from venus8 import updater
        with mock.patch.object(updater.os, "name", "nt"), \
                mock.patch.object(updater.subprocess, "Popen") as popen:
            updater.run_installer("C:/tmp/Venus-8-v9.9.9-Windows-Setup.exe")
        args = popen.call_args[0][0]
        self.assertIn("/SILENT", args)
        self.assertIn("/CLOSEAPPLICATIONS", args)


if __name__=="__main__":
    unittest.main()
