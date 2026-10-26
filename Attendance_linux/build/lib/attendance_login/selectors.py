"""実HTMLで照合済みのSeleniumロケーター。"""

from selenium.webdriver.common.by import By

SSO_LOGIN_BUTTON = (By.CSS_SELECTOR, "#idp_hint > button")
OTHER_ACCOUNT_LINK = (By.ID, "cancel_idp_hint")
SALESFORCE_LOGIN_FORM = (By.ID, "login_form")
SALESFORCE_USERNAME = (By.ID, "username")
SALESFORCE_PASSWORD = (By.ID, "password")
SALESFORCE_DIRECT_LOGIN_BUTTON = (By.ID, "Login")
LOGIN_ERROR = (By.ID, "error")
LOGIN_START_URL = (By.ID, "login_startUrl")
SAVED_ACCOUNT_LIST = (By.ID, "idlist")

MS_ACCOUNT_LIST = (By.ID, "tilesHolder")
MS_OTHER_ACCOUNT = (By.ID, "otherTile")
MS_SUBMIT = (By.ID, "idSIButton9")

SALESFORCE_HEADER = (By.ID, "oneHeader")
TIME_ATTENDANCE_TAB = (
    By.CSS_SELECTOR,
    '[data-target-selection-name="sfdc:TabDefinition.tex__TimeAttendance"]',
)
TIME_ATTENDANCE_IFRAME = (By.CSS_SELECTOR, ".iframe-parent > iframe")
ALL_IFRAMES = (By.TAG_NAME, "iframe")
TIME_ATTENDANCE_HEADING = (
    By.CSS_SELECTOR,
    "h1.timesheet-pc-main-content__header-heading",
)
TIME_ATTENDANCE_DAILY_ROWS = (
    By.CSS_SELECTOR,
    "tr.timesheet-pc-main-content-timesheet-daily-row",
)
DAILY_ROW_DATE = (
    By.CSS_SELECTOR,
    "td.timesheet-pc-main-content-timesheet-daily-row__col-date",
)
DAILY_ROW_START_BUTTON = (
    By.CSS_SELECTOR,
    "td.timesheet-pc-main-content-timesheet-daily-row__col-start-time button",
)
DAILY_ROW_END_BUTTON = (
    By.CSS_SELECTOR,
    "td.timesheet-pc-main-content-timesheet-daily-row__col-end-time button",
)
DAILY_ROW_WORKLOAD_BUTTON = (
    By.CSS_SELECTOR,
    "button[data-testid='timesheet-pc__daily-summary-button']",
)
DAILY_ROW_REQUEST_BUTTON = (
    By.CSS_SELECTOR,
    "button.timesheet-pc-main-content-timesheet-request-button-with-status",
)
DAILY_ROW_APPLICATION_STATUS = (
    By.XPATH,
    ".//div[@title='未申請' or @title='申請中' or @title='承認済' "
    "or @title='差戻し']",
)
DAILY_ROW_SAVE_BUTTON = (
    By.CSS_SELECTOR,
    "td.timesheet-pc-main-content-timesheet-display-field-layout-item-row__button "
    "button",
)
DAILY_ROW_WORKPLACE_BUTTON = (
    By.CSS_SELECTOR,
    "td.timesheet-pc-main-content-timesheet-display-field-layout-item-row__dropdown "
    "button[aria-haspopup='listbox']",
)
DAILY_ROW_BUSINESS_CONTENT_INPUT = (
    By.CSS_SELECTOR,
    "td.timesheet-pc-main-content-timesheet-display-field-layout-item-row__dropdown "
    "+ td.timesheet-pc-main-content-timesheet-display-field-layout-item-row__text "
    "input",
)
WORKPLACE_OPTIONS = (
    By.CSS_SELECTOR,
    "[role='listbox'] [role='option']",
)
WORK_TIME_DIALOG = (
    By.CSS_SELECTOR,
    '[class*="DailyAttTimeDialog__Wrapper"]',
)
WORK_TIME_DIALOG_TITLE = (
    By.CSS_SELECTOR,
    '[class*="Dialog__TitleContainer"]',
)
WORK_TIME_DIALOG_DATE = (By.CSS_SELECTOR, "time[datetime]")
WORK_TIME_START_INPUT = (
    By.XPATH,
    ".//*[contains(@class, 'FieldItem__FieldItemContainer')]["
    ".//*[contains(@class, 'FieldItem__Label') and normalize-space()='出勤']"
    "]//input",
)
WORK_TIME_END_INPUT = (
    By.XPATH,
    ".//*[contains(@class, 'FieldItem__FieldItemContainer')]["
    ".//*[contains(@class, 'FieldItem__Label') and normalize-space()='退勤']"
    "]//input",
)
WORK_TIME_SAVE_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='保存']",
)
WORK_TIME_REQUEST_STATUS = (
    By.CSS_SELECTOR,
    "[class*='RequestStatusChip__StyledChip']",
)
WORK_TIME_REQUEST_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='申請']",
)
WORK_TIME_CANCEL_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='キャンセル']",
)
WORKLOAD_DIALOG = (
    By.CSS_SELECTOR,
    '[class*="components__StyledDialog"]',
)
WORKLOAD_DIALOG_TITLE = (
    By.XPATH,
    ".//*[contains(@class, 'Header__Title') and "
    "normalize-space()='デイリーサマリー']",
)
WORKLOAD_DIALOG_DATE = (
    By.CSS_SELECTOR,
    "input[class*='DatePicker__StyledDatePicker']",
)
WORKLOAD_TASK_ROWS = (
    By.CSS_SELECTOR,
    "[class*='DraggableTaskRow__TaskRowWrapper']",
)
WORKLOAD_TASK_JOB_CODE = (
    By.CSS_SELECTOR,
    "[class*='TaskRow__Job'] span",
)
WORKLOAD_TASK_TIME_INPUT = (
    By.CSS_SELECTOR,
    "input[class*='Combobox__Input']",
)
WORKLOAD_ACTUAL_TIME = (
    By.CSS_SELECTOR,
    "[class*='Header__Time']",
)
WORKLOAD_SAVE_AND_CLOSE_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='保存して閉じる']",
)
WORKLOAD_CANCEL_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='キャンセル']",
)

DAILY_REQUEST_DIALOG = (
    By.CSS_SELECTOR,
    ".timesheet-pc-dialogs-daily-att-request-dialog",
)
DAILY_REQUEST_DIALOG_DATE = (
    By.CSS_SELECTOR,
    "time.timesheet-pc-dialogs-daily-att-request-dialog__date",
)
DAILY_REQUEST_CANCEL_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='キャンセル']",
)
DAILY_REQUEST_WORK_TIME_CHANGE_BUTTON = (
    By.XPATH,
    ".//button[.//div[normalize-space()='勤務時間変更']]",
)
DAILY_REQUEST_SUBMIT_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='申請']",
)
DAILY_REQUEST_WITHDRAW_BUTTON = (
    By.XPATH,
    ".//button[normalize-space()='取消し']",
)
MONTHLY_STATUS = (
    By.CSS_SELECTOR,
    ".timesheet-pc-request__status__value",
)
MONTHLY_CONFIRM_BUTTON = (
    By.XPATH,
    "//button[.//span[normalize-space()='月次勤務確定']]",
)

SALESFORCE_LOGIN_HOST = "meitecgroup.my.salesforce.com"
MICROSOFT_LOGIN_HOST = "login.microsoftonline.com"
TIME_ATTENDANCE_HOST = "meitecgroup.lightning.force.com"
TIME_ATTENDANCE_PATH = "/lightning/n/tex__TimeAttendance"
