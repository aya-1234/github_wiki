from unittest import TestCase
from unittest.mock import patch

from attendance_login.pacing import RequestPacer


class RequestPacerTest(TestCase):
    def test_first_request_starts_without_sleeping(self) -> None:
        pacer = RequestPacer(5)
        with (
            patch("attendance_login.pacing.time.monotonic", return_value=100.0),
            patch("attendance_login.pacing.time.sleep") as sleep,
        ):
            pacer.wait_for_slot()
        sleep.assert_not_called()

    def test_waits_only_for_remaining_interval(self) -> None:
        pacer = RequestPacer(5)
        with (
            patch(
                "attendance_login.pacing.time.monotonic",
                side_effect=[100.0, 102.0, 105.0],
            ),
            patch("attendance_login.pacing.time.sleep") as sleep,
        ):
            pacer.wait_for_slot()
            pacer.wait_for_slot()
        sleep.assert_called_once_with(3.0)

    def test_does_not_sleep_after_interval_has_elapsed(self) -> None:
        pacer = RequestPacer(5)
        with (
            patch(
                "attendance_login.pacing.time.monotonic",
                side_effect=[100.0, 106.0],
            ),
            patch("attendance_login.pacing.time.sleep") as sleep,
        ):
            pacer.wait_for_slot()
            pacer.wait_for_slot()
        sleep.assert_not_called()

    def test_zero_delay_disables_sleeping(self) -> None:
        pacer = RequestPacer(0)
        with (
            patch(
                "attendance_login.pacing.time.monotonic",
                side_effect=[100.0, 100.0],
            ),
            patch("attendance_login.pacing.time.sleep") as sleep,
        ):
            pacer.wait_for_slot()
            pacer.wait_for_slot()
        sleep.assert_not_called()
