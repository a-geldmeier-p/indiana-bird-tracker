"""Offline checks for browser-script safety normalization."""

import unittest

from tutorial_script_safety import prepare_recording_script


class TutorialScriptSafetyTests(unittest.TestCase):
    def test_leaflet_pane_wait_uses_a_visible_polygon(self):
        script = (
            "await page.locator('#map-county_map .leaflet-overlay-pane').waitFor();"
        )
        self.assertEqual(
            prepare_recording_script(script),
            "await page.locator('#map-county_map .leaflet-interactive')"
            ".first().waitFor();",
        )

    def test_unrelated_workflows_remain_unchanged(self):
        script = "await page.getByRole('heading', { name: 'Dashboard' }).waitFor();"
        self.assertEqual(prepare_recording_script(script), script)


if __name__ == "__main__":
    unittest.main()
