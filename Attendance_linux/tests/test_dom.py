from unittest import TestCase
from unittest.mock import MagicMock

from attendance_login.dom import scan_open_shadow_dom


class ShadowDomScanTest(TestCase):
    def test_returns_iframes_found_inside_open_shadow_roots(self) -> None:
        driver = MagicMock()
        normal_frame = MagicMock()
        shadow_frame = MagicMock()
        driver.execute_script.return_value = {
            "frames": [normal_frame, shadow_frame],
            "shadowRootCount": 2,
        }

        frames, root_count = scan_open_shadow_dom(driver)

        self.assertEqual(frames, [normal_frame, shadow_frame])
        self.assertEqual(root_count, 2)
        driver.find_elements.assert_not_called()

    def test_falls_back_to_normal_dom_search(self) -> None:
        driver = MagicMock()
        frame = MagicMock()
        driver.execute_script.return_value = None
        driver.find_elements.return_value = [frame]

        frames, root_count = scan_open_shadow_dom(driver)

        self.assertEqual(frames, [frame])
        self.assertIsNone(root_count)
