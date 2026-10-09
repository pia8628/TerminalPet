"""CI 演練用：故意只在 GitHub Actions 上失敗，用來確認紅燈會擋住合併。演練完即移除。"""

import os


def test_ci_drill_fails_on_ci():
    assert os.environ.get("GITHUB_ACTIONS") != "true", "CI 演練：故意失敗"
