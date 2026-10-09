# 專案協作規則

<!-- 由 dev-kickoff 生成於 2026-10-09，模板版本 v4 -->

## 專案資訊

- 專案名稱：TerminalPet（監看 Claude Code 各 session 狀態的桌面小工具）
- 類型：Python（PySide6 桌面程式＋Git Bash hooks 腳本）
- 部署平台：GitHub Release（PyInstaller 打包 exe，`scripts/build.ps1`）＋ Claude Code plugin marketplace（`.claude-plugin/`、`hooks/`）
- 資料庫：無（狀態以 JSON 檔存在 `~/.terminalpet/`）

## 使用者背景

使用者是非工程師（生產管理背景，vibe coding 經驗）。專有名詞、技術選型需先說明概念、優缺點、風險，再由使用者決定。

## 紅線（違反任一條即停下，先取得使用者同意）

1. **先討論再動手**：新模組、新檔案、架構或選型變更，先提案並取得同意才實作。功能變更走 dev 流程：`/dev-spec` 產規格（Codex 交叉審查 → 使用者核准；規格階段不碰程式碼）→ `/dev-tickets` 拆任務卡（使用者核准）→ `/dev-next-card` 逐卡實作或 `/dev-run-card` 長線連做 → 每張卡 `/dev-verify-card` 即時驗收 → 全部完成後 `/dev-verify-spec` 驗收並合併進 `docs/specs/SPEC.md`。構想大到寫不出規格時，先走 `/dev-wayfinder` 探路。
2. **業務邏輯要使用者驗算**：涉及金額、結餘、日期規則等計算，完成後必須用具體數字舉例請使用者驗算，不得自行宣告正確。
3. **危險操作白話文確認**：執行 rm／資料庫 migration／改 git 歷史／權限變更前，先用白話文說明「這會做什麼、影響什麼、能否復原」，確認後才執行。
4. **資料庫預設 RLS**：涉及資料庫的功能，設計階段就規劃 Row-Level Security；預設拒絕，明確寫政策才放行。
5. **git 一律走 git-commit skill**：不直接下 git commit / push 指令。功能分支上可以主動 commit（git-commit 的分支模式）；`main` 上的 commit 要使用者確認；**push 一律等使用者明說，不主動 push**。
6. **套件安裝先查證**：安裝任何非主流套件前，先到 npm / PyPI 確認套件存在、下載量、維護狀態，回報使用者後才安裝（防幻覺套件）。

## 架構與程式紀律

> 每一條都要答得出「怎麼檢查它有沒有被遵守」。答不出來的規則是口號，不要寫進來。
> 由 dev-kickoff 與使用者討論後填；個人腳本、純靜態網頁等不適用的項目寫「不適用」。

- **分層與相依方向**：單向資料流——hooks 寫狀態檔，桌寵只讀與顯示。

  | 層 | 位置 | 職責 | 禁止 |
  |----|------|------|------|
  | 狀態寫入端（hooks） | `scripts/pet-state.sh`、`set_state.py`、`hooks/hooks.json` | 依 Claude Code hook 事件建立／更新 `~/.terminalpet/sessions/<sid>.json` | 不 import PySide6、不碰 UI |
  | 顯示端（桌寵） | `pet.py` | 讀 session 檔、彙整狀態、顯示與右鍵操作；只寫自己的設定檔 `config.json` | 不建立、不改寫 session 檔（只允許刪除：過期清理與使用者手動移除） |
  | 安裝／打包 | `install.py`、`installer/`、`build/`、`scripts/build.ps1` | 安裝 hooks、打包 exe | 不放執行期邏輯 |

  檢查方式：`grep -n "write_text\|open(.*w" pet.py` 只應出現 `CONFIG_FILE`；`grep -n PySide6 set_state.py scripts/pet-state.sh` 應無結果。
- **統一回應與錯誤格式**：不適用（無 API）。hooks 腳本出錯時必須靜默結束、不得讓 Claude Code 的 hook 失敗或卡住（檢查：hooks 皆為 `async: true`，腳本不以非零碼離開）。
- **完成定義（Definition of Done）**：卡的驗收條件逐條對照打勾、既有測試與 lint 全綠、「驗證證據」已填、AC 編號可對帳。「畫面看起來可以」不算完成。
- **命名與檔案位置**：session 狀態值只用 `waiting / done / working / thinking / idle` 五種（`end` 是刪除指令不是狀態值；寫入端與 `pet.py` 的 `STATE_PRIORITY` 必須一致）；測試放 `tests/`，檔名 `test_<被測模組>.py`。

## 開發慣例

- 分支策略採簡化版：`main` + `feature/*`，重要變更才開 PR（要升級完整 Git Flow 時參考 dev-ci-setup skill）
- `docs/specs/SPEC.md` 是系統行為的唯一真相總帳：開發任何功能前先讀；只寫行為不寫實作；只有 `/dev-verify-spec` 驗收通過的內容能合併進去（唯一例外：`/dev-spec` 輕量通道、經使用者確認的小改動，在版本紀錄補一行）
- 規格用編號對帳：`US-代號-NN`、`AC-代號-NN`；任務卡、測試名稱、驗收 Hub 都引用同一組編號
- 可遷移到其他專案的開發經驗 → 記入 `dev_exp.md`
- 進度與待辦 → 更新 `專案進度追蹤.md`；延後的測試項目必須寫進去，不可只留在對話中
- 環境變數一律放 `.env`（已在 .gitignore），程式碼中不得出現金鑰
- 測試不得連正式資料庫，一律用測試資料庫或 mock
- AI 自驗時看回應內容與欄位，不只看狀態碼；健康檢查要真的碰到依賴（資料庫），不是只回 OK

## 階段入口

- 想法還很模糊：`/dev-wayfinder`（探路，產出決策卡地圖）
- 功能開發：`/dev-spec`（規格；內含 `codex-peer-review` 交叉審查）→ `/dev-tickets`（拆任務卡）
- 逐卡實作：開新對話 `/dev-next-card`（一個對話一張卡，做完接 `/dev-verify-card` 即時驗收）
- 一次連續做完多張卡：`/dev-run-card`（長線模式，在功能分支上逐卡施工、自動 commit 不 push，人工驗收集中到最後）
- 單卡驗收：`/dev-verify-card`；整個 change 驗收與合併規格：`/dev-verify-spec`
- 抓 bug：`/dev-debug`
- 規劃測試：`/dev-test-plan`
- 初始化 CI/CD：`/dev-ci-setup`
- 專案收尾：`/dev-closeout`
