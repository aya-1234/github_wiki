"""通常DOMとopen Shadow DOMを横断する探索処理。"""

from __future__ import annotations

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

from . import selectors


_SHADOW_DOM_SCAN_SCRIPT = """
const frames = [];
const roots = [document];
let shadowRootCount = 0;

for (let index = 0; index < roots.length; index += 1) {
    const root = roots[index];
    frames.push(...root.querySelectorAll("iframe"));
    for (const element of root.querySelectorAll("*")) {
        if (element.shadowRoot) {
            roots.push(element.shadowRoot);
            shadowRootCount += 1;
        }
    }
}
return {frames, shadowRootCount};
"""


def scan_open_shadow_dom(
    driver: WebDriver,
) -> tuple[list[WebElement], int | None]:
    """通常DOMとopen Shadow DOM内のiframe、Shadow Root数を返す。"""
    try:
        result = driver.execute_script(_SHADOW_DOM_SCAN_SCRIPT)
        if isinstance(result, dict):
            frames = result.get("frames")
            root_count = result.get("shadowRootCount")
            if isinstance(frames, list):
                return (
                    frames,
                    root_count if isinstance(root_count, int) else None,
                )
    except WebDriverException:
        pass

    # JavaScript実行が利用できない場合も通常DOMの探索は継続する。
    return driver.find_elements(*selectors.ALL_IFRAMES), None
