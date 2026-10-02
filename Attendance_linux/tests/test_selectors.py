from pathlib import Path
from unittest import TestCase

from attendance_login import selectors


ROOT = Path(__file__).resolve().parents[1]


class SelectorFixtureTest(TestCase):
    def test_salesforce_login_fixture_contains_fixed_selectors(self) -> None:
        html = (
            ROOT / "use_html/1/次を使用してログイン _ Salesforce.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(html.count('id="idp_hint"'), 1)
        self.assertEqual(html.count('id="login_form"'), 1)

    def test_microsoft_fixture_contains_fixed_selectors(self) -> None:
        html = (
            ROOT / "use_html/2/アカウントにサインイン.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(html.count('id="tilesHolder"'), 1)
        self.assertEqual(html.count('id="otherTile"'), 1)

    def test_attendance_fixture_contains_fixed_selectors(self) -> None:
        html = (
            ROOT / "use_html/3/勤務表 _ Salesforce.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            html.count(
                'data-target-selection-name="'
                'sfdc:TabDefinition.tex__TimeAttendance"'
            ),
            1,
        )
        self.assertIn("iframe-parent", html)

    def test_configured_path(self) -> None:
        self.assertEqual(
            selectors.TIME_ATTENDANCE_PATH,
            "/lightning/n/tex__TimeAttendance",
        )

    def test_work_time_dialog_fixture_contains_input_elements(self) -> None:
        html = (
            ROOT
            / "use_html/6/勤務時間表 _ Salesforce_files/saved_resource.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(html.count(">勤務時間入力<"), 1)
        self.assertIn('value="09:00"', html)
        self.assertIn('value="17:45"', html)
        self.assertEqual(
            html.count(
                'type="submit" class="Button-sc-w4yovf-0 blLfaK">保存'
            ),
            1,
        )
        self.assertEqual(
            selectors.WORK_TIME_SAVE_BUTTON[1],
            ".//button[normalize-space()='保存']",
        )

    def test_workload_dialog_fixture_contains_fixed_elements(self) -> None:
        html = (
            ROOT
            / "use_html/5/勤務(工数)表 _ Salesforce_files/saved_resource.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(html.count(">デイリーサマリー<"), 1)
        self.assertEqual(html.count(">工数入力<"), 1)
        self.assertIn("DraggableTaskRow__TaskRowWrapper", html)
        self.assertIn("Combobox__Input", html)
        self.assertEqual(html.count(">保存して閉じる<"), 1)

    def test_application_fixture_contains_fixed_elements(self) -> None:
        html = (
            ROOT
            / "use_html/4/勤務表 _ Salesforce_files/saved_resource.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "timesheet-pc-dialogs-daily-att-request-dialog__date", html
        )
        self.assertIn(">申請済み<", html)
        self.assertIn(">取消し<", html)

    def test_latest_daily_request_fixture_contains_request_flow(self) -> None:
        html = (
            ROOT
            / "use_html/7/勤務表 申請_ Salesforce_files/saved_resource.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "timesheet-pc-dialogs-daily-att-request-dialog__date", html
        )
        self.assertIn(">勤務時間変更<", html)
        self.assertIn(">取消し<", html)

    def test_latest_workload_fixture_contains_configured_job(self) -> None:
        html = (
            ROOT
            / "use_html/8/勤務表 工数_ Salesforce_files/saved_resource.html"
        ).read_text(encoding="utf-8")
        self.assertIn(">デイリーサマリー<", html)
        self.assertIn(">JOB_SGY_44872243_01_01<", html)
        self.assertIn('value="07:45"', html)
