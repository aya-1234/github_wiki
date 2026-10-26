from io import BytesIO
from unittest import TestCase
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from attendance_login.errors import NotificationError
from attendance_login.notifier import safe_url, send_notification


class SafeUrlTest(TestCase):
    def test_removes_query_and_fragment(self) -> None:
        self.assertEqual(
            safe_url("https://example.com/path?token=secret#fragment"),
            "https://example.com/path",
        )


class SendNotificationTest(TestCase):
    def test_skips_when_url_is_empty(self) -> None:
        with patch("attendance_login.notifier.urlopen") as urlopen:
            send_notification("", "EVENT", "message", "", 5)
        urlopen.assert_not_called()

    def test_succeeds_without_retry_on_2xx(self) -> None:
        response = MagicMock()
        response.status = 204
        response.__enter__.return_value = response
        with patch(
            "attendance_login.notifier.urlopen", return_value=response
        ) as urlopen:
            send_notification(
                "https://example.com/webhook",
                "EVENT",
                "message",
                "https://example.com/path?secret=value",
                5,
            )
        self.assertEqual(urlopen.call_count, 1)

    def test_does_not_retry_4xx(self) -> None:
        error = HTTPError(
            "https://example.com/webhook", 400, "Bad Request", {}, BytesIO()
        )
        with patch(
            "attendance_login.notifier.urlopen", side_effect=error
        ) as urlopen:
            with self.assertRaises(NotificationError):
                send_notification(
                    "https://example.com/webhook",
                    "EVENT",
                    "message",
                    "",
                    5,
                )
        self.assertEqual(urlopen.call_count, 1)

    def test_retries_5xx_once(self) -> None:
        error = HTTPError(
            "https://example.com/webhook",
            500,
            "Server Error",
            {},
            BytesIO(),
        )
        with (
            patch(
                "attendance_login.notifier.urlopen", side_effect=error
            ) as urlopen,
            patch("attendance_login.notifier.time.sleep"),
        ):
            with self.assertRaises(NotificationError):
                send_notification(
                    "https://example.com/webhook",
                    "EVENT",
                    "message",
                    "",
                    5,
                )
        self.assertEqual(urlopen.call_count, 2)
