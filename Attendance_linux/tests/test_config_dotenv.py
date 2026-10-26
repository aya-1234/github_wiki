"""config.py の .env 自動読込（_load_dotenv）の単体テスト。"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from attendance_login.config import (
    _load_dotenv,
    _parse_dotenv_line,
    Config,
)

# Config.from_env() が参照する環境変数の一覧（退避・復元対象）
CONFIG_ENV_KEYS: tuple[str, ...] = (
    "DOTENV_PATH",
    "ATTENDANCE_TOP_URL",
    "CHROME_USER_DATA_DIR",
    "CHROME_PROFILE_DIRECTORY",
    "TARGET_ACCOUNT",
    "WEBHOOK_URL",
    "LOGIN_TIMEOUT_SECONDS",
    "PAGE_LOAD_TIMEOUT_SECONDS",
    "WEBHOOK_TIMEOUT_SECONDS",
    "HEADLESS",
    "KEEP_BROWSER_OPEN_ON_ERROR",
    "LOG_LEVEL",
    "LOG_FILE",
    "LOG_RETENTION_DAYS",
    "WORK_START_TIME",
    "WORK_END_TIME",
    "WORK_PLACE",
    "BUSINESS_CONTENT",
    "WORK_INPUT_TIMEOUT_SECONDS",
    "WORKLOAD_ENABLED",
    "WORKLOAD_FILE",
    "WORKLOAD_ALLOW_OVERWRITE",
    "WORKLOAD_TOLERANCE_MINUTES",
    "APPLICATION_ENABLED",
    "APPLICATION_CONFIRM_ONLY",
    "APPLICATION_AUTO_SUBMIT",
    "DAILY_REQUEST_ENABLED",
)


class DotenvParserTest(TestCase):
    """_parse_dotenv_line のパース仕様テスト。"""

    def test_key_value(self) -> None:
        self.assertEqual(
            _parse_dotenv_line("KEY=value"), ("KEY", "value")
        )

    def test_skips_blank_and_comment_line(self) -> None:
        self.assertIsNone(_parse_dotenv_line(""))
        self.assertIsNone(_parse_dotenv_line("   "))
        self.assertIsNone(_parse_dotenv_line("# comment"))
        self.assertIsNone(_parse_dotenv_line("   # comment"))

    def test_strips_whitespace_around_value(self) -> None:
        self.assertEqual(
            _parse_dotenv_line("KEY = value "), ("KEY", "value")
        )

    def test_export_prefix(self) -> None:
        self.assertEqual(
            _parse_dotenv_line("export KEY=value"), ("KEY", "value")
        )
        self.assertEqual(
            _parse_dotenv_line("export KEY = value "), ("KEY", "value")
        )

    def test_quoted_values(self) -> None:
        self.assertEqual(
            _parse_dotenv_line("KEY='value'"), ("KEY", "value")
        )
        self.assertEqual(
            _parse_dotenv_line('KEY="value"'), ("KEY", "value")
        )
        self.assertEqual(
            _parse_dotenv_line('KEY="va lue"'), ("KEY", "va lue")
        )

    def test_inline_comment_removed_when_unquoted(self) -> None:
        self.assertEqual(
            _parse_dotenv_line("KEY=value # comment"), ("KEY", "value")
        )

    def test_comment_inside_quotes_not_split(self) -> None:
        self.assertEqual(
            _parse_dotenv_line('KEY="v#lue"'), ("KEY", "v#lue")
        )


class DotenvLoadTest(TestCase):
    """_load_dotenv / Config.from_env の統合テスト。"""

    def setUp(self) -> None:
        # 環境変数の退避（対象キーをすべてクリアしてテストを開始する）
        self._saved: dict[str, str] = {}
        for key in CONFIG_ENV_KEYS:
            if key in os.environ:
                self._saved[key] = os.environ.pop(key)

    def tearDown(self) -> None:
        # 環境変数の復元
        for key in CONFIG_ENV_KEYS:
            os.environ.pop(key, None)
        os.environ.update(self._saved)

    def test_from_env_reads_dotenv(self) -> None:
        """環境変数が空でも .env から値を読み込めること。"""
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "# コメント行",
                        "CHROME_USER_DATA_DIR={0}".format(directory),
                        "TARGET_ACCOUNT=user@example.com",
                        "HEADLESS=true",
                        "LOG_FILE={0}/app.log".format(directory),
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["DOTENV_PATH"] = str(dotenv)
            config = Config.from_env()
        self.assertEqual(config.user_data_dir, Path(directory))
        self.assertEqual(config.target_account, "user@example.com")
        self.assertTrue(config.headless)
        self.assertEqual(config.log_file, Path(directory) / "app.log")

    def test_existing_env_overrides_dotenv(self) -> None:
        """既存の環境変数がある場合は .env が上書きしないこと。"""
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "CHROME_USER_DATA_DIR={0}".format(directory),
                        "TARGET_ACCOUNT=from_dotenv@example.com",
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["DOTENV_PATH"] = str(dotenv)
            os.environ["CHROME_USER_DATA_DIR"] = "/tmp/existing-profile"
            os.environ["TARGET_ACCOUNT"] = "from_env@example.com"
            config = Config.from_env()
        self.assertEqual(
            config.user_data_dir, Path("/tmp/existing-profile")
        )
        self.assertEqual(config.target_account, "from_env@example.com")

    def test_load_dotenv_handles_export_and_quotes(self) -> None:
        """export プレフィックスとクォートのパース。"""
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "export CHROME_USER_DATA_DIR={0}".format(directory),
                        'export TARGET_ACCOUNT="user@example.com"',
                        "export WEBHOOK_URL='https://example.com/hook'",
                        "HEADLESS=true",
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["DOTENV_PATH"] = str(dotenv)
            _load_dotenv()
        self.assertEqual(os.environ["CHROME_USER_DATA_DIR"], directory)
        self.assertEqual(os.environ["TARGET_ACCOUNT"], "user@example.com")
        self.assertEqual(
            os.environ["WEBHOOK_URL"], "https://example.com/hook"
        )
        self.assertEqual(os.environ["HEADLESS"], "true")

    def test_load_dotenv_inline_and_comment_lines(self) -> None:
        """コメント行・空行・インラインコメントを正しく処理すること。"""
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "# 全体コメント",
                        "CHROME_USER_DATA_DIR={0} # プロファイル置き場".format(directory),
                        "",
                        "TARGET_ACCOUNT=user@example.com",
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["DOTENV_PATH"] = str(dotenv)
            _load_dotenv()
        self.assertEqual(os.environ["CHROME_USER_DATA_DIR"], directory)
        self.assertEqual(os.environ["TARGET_ACCOUNT"], "user@example.com")

    def test_load_dotenv_missing_file_does_nothing(self) -> None:
        """.env が存在しない場合は何もせず例外も出さないこと。

        検索結果を None（ファイルなし）にモックして、
        プロジェクトルートの .env に依存しない検証にする。
        """
        with TemporaryDirectory() as directory:
            os.environ["DOTENV_PATH"] = str(Path(directory) / "missing.env")
            with patch(
                "attendance_login.config._find_dotenv_path",
                return_value=None,
            ):
                _load_dotenv()  # 例外が出ないこと
        self.assertNotIn("TARGET_ACCOUNT", os.environ)

    def test_load_dotenv_does_not_overwrite_existing(self) -> None:
        """os.environ に存在するキーを .env が上書きしないこと。"""
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(
                "CHROME_USER_DATA_DIR={0}\n".format(directory),
                encoding="utf-8",
            )
            os.environ["DOTENV_PATH"] = str(dotenv)
            os.environ["CHROME_USER_DATA_DIR"] = "/tmp/keep-me"
            _load_dotenv()
        self.assertEqual(
            os.environ["CHROME_USER_DATA_DIR"], "/tmp/keep-me"
        )
