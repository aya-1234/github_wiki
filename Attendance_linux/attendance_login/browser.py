"""Chrome WebDriverの生成。"""

from __future__ import annotations

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from .config import Config
from .errors import BrowserStartupError


def create_driver(config: Config) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={config.user_data_dir}")
    if config.profile_directory:
        options.add_argument(f"--profile-directory={config.profile_directory}")
    if config.headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--start-maximized")

    try:
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(config.page_load_timeout)
        return driver
    except WebDriverException as exc:
        raise BrowserStartupError(
            "Chromeを起動できません。プロファイル競合とChromeの状態を確認してください"
        ) from exc
