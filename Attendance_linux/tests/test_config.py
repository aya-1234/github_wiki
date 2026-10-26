from __future__ import annotations

import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from attendance_login.config import Config, DEFAULT_TOP_URL
from attendance_login.errors import ConfigurationError


class ConfigTest(TestCase):
    def setUp(self) -> None:
        # .env 自動読込の追加に伴い、テストが実在の .env に依存しないよう
        # _load_dotenv を無効化する（環境変数は clear=True で厳密に制御する）
        self._dotenv_patcher = patch(
            "attendance_login.config._load_dotenv", return_value=None
        )
        self._dotenv_patcher.start()
        self.addCleanup(self._dotenv_patcher.stop)

    def base_env(self) -> dict[str, str]:
        return {
            "CHROME_USER_DATA_DIR": "/tmp/attendance-profile",
            "TARGET_ACCOUNT": "user@example.com",
        }

    def test_loads_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            env = self.base_env() | {"CHROME_USER_DATA_DIR": directory}
            with patch.dict(os.environ, env, clear=True):
                config = Config.from_env()
                config.validate_runtime_paths()
        self.assertEqual(config.top_url, DEFAULT_TOP_URL)
        self.assertEqual(config.login_timeout, 60)
        self.assertEqual(config.work_start_time, "09:00")
        self.assertEqual(config.work_end_time, "17:45")
        self.assertEqual(config.work_place, "出社")
        self.assertEqual(config.business_content, "開発業務")
        self.assertEqual(config.work_input_timeout, 10)
        self.assertEqual(config.server_request_delay_seconds, 5)
        self.assertFalse(config.workload_enabled)
        self.assertFalse(config.application_enabled)
        self.assertTrue(config.application_confirm_only)
        self.assertFalse(config.application_auto_submit)
        self.assertFalse(config.daily_request_enabled)
        self.assertFalse(config.headless)

    def test_requires_profile_path(self) -> None:
        with patch.dict(
            os.environ, {"TARGET_ACCOUNT": "user@example.com"}, clear=True
        ):
            with self.assertRaises(ConfigurationError):
                Config.from_env()

    def test_requires_target_account(self) -> None:
        with patch.dict(
            os.environ,
            {"CHROME_USER_DATA_DIR": "/tmp/attendance-profile"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationError):
                Config.from_env()

    def test_rejects_invalid_timeout(self) -> None:
        env = self.base_env() | {"LOGIN_TIMEOUT_SECONDS": "0"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                Config.from_env()

    def test_loads_server_request_delay_boundaries(self) -> None:
        for value in ("0", "300"):
            with self.subTest(value=value):
                env = self.base_env() | {
                    "SERVER_REQUEST_DELAY_SECONDS": value
                }
                with patch.dict(os.environ, env, clear=True):
                    config = Config.from_env()
                self.assertEqual(
                    config.server_request_delay_seconds, int(value)
                )

    def test_rejects_server_request_delay_outside_range(self) -> None:
        for value in ("-1", "301"):
            with self.subTest(value=value):
                env = self.base_env() | {
                    "SERVER_REQUEST_DELAY_SECONDS": value
                }
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(ConfigurationError):
                        Config.from_env()

    def test_rejects_missing_profile_directory(self) -> None:
        with patch.dict(os.environ, self.base_env(), clear=True):
            config = Config.from_env()
        with self.assertRaises(ConfigurationError):
            config.validate_runtime_paths()

    def test_loads_configured_work_values(self) -> None:
        env = self.base_env() | {
            "WORK_START_TIME": "08:30",
            "WORK_END_TIME": "18:00",
            "WORK_PLACE": "在宅",
            "BUSINESS_CONTENT": "設計業務",
            "WORK_INPUT_TIMEOUT_SECONDS": "20",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
        self.assertEqual(config.work_start_time, "08:30")
        self.assertEqual(config.work_end_time, "18:00")
        self.assertEqual(config.work_place, "在宅")
        self.assertEqual(config.business_content, "設計業務")
        self.assertEqual(config.work_input_timeout, 20)

    def test_rejects_invalid_work_time(self) -> None:
        env = self.base_env() | {"WORK_START_TIME": "9:00"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                Config.from_env()

    def test_workload_requires_file_setting(self) -> None:
        env = self.base_env() | {"WORKLOAD_ENABLED": "true"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                Config.from_env()

    def test_auto_submit_requires_application_enabled(self) -> None:
        env = self.base_env() | {"APPLICATION_AUTO_SUBMIT": "true"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                Config.from_env()

    def test_auto_submit_requires_confirmation_mode_off(self) -> None:
        env = self.base_env() | {
            "APPLICATION_ENABLED": "true",
            "APPLICATION_AUTO_SUBMIT": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigurationError):
                Config.from_env()
