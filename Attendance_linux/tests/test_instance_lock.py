from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from attendance_login.errors import BrowserStartupError
from attendance_login.instance_lock import profile_lock


class ProfileLockTest(TestCase):
    def test_rejects_second_lock(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            with profile_lock(path):
                with self.assertRaises(BrowserStartupError):
                    with profile_lock(path):
                        pass

    def test_does_not_unlock_when_lock_acquisition_fails(self) -> None:
        handle = MagicMock()
        handle_context = MagicMock()
        handle_context.open.return_value = handle

        with (
            patch.object(Path, "open", handle_context.open),
            patch(
                "attendance_login.instance_lock._try_lock",
                side_effect=OSError("already locked"),
            ),
            patch("attendance_login.instance_lock._unlock") as unlock,
        ):
            with self.assertRaises(BrowserStartupError):
                with profile_lock(Path("profile")):
                    pass

        unlock.assert_not_called()
        handle.close.assert_called_once_with()
