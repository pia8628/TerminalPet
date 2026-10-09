# 01-可行性實驗：列出 WT 分頁並依標題切換

**做完能 demo 什麼**：執行一支實驗腳本並傳入一個 session 標題，腳本就會把對應的 Windows Terminal 分頁切到最前面（包括所在視窗已最小化的情況）；同時產出一份實驗結論，回答規格中待確認的五個問題。

**Blocked by**：無——可直接開工

**狀態**：已完成（檢查點觸發：狀態前綴清單需修訂，見實作備註）

**檢查點**：是（實驗失敗或結果和規格假設不同時，要先回頭修訂 delta.md，後面的卡才能開工）

## 規格依據

- 無——技術前置（驗證 delta.md「Implementation Decisions」的假設：標題比對、`/rename`、狀態前綴字元、最小化還原、前景切換）

## 驗收條件

- [x] 技術：用 UI Automation 列出所有 WT 視窗（class `CASCADIA_HOSTING_WINDOW_CLASS`）的所有分頁名稱
- [x] 技術：從對話紀錄檔（JSONL）的最後 1 MB 取出 session 標題（`custom-title` 優先，否則用最後一筆 `ai-title`），和分頁名稱比對成功
- [x] 技術：`/rename` 改名後，分頁標題是否會顯示新名稱——記下結果（不會顯示的話，回頭修訂 AC-JUMP-06）〔結果：會顯示（依 Claude Code 程式碼推論，本機無改名紀錄可實測），AC-JUMP-06 不需修訂；實際改名後的分頁標題列入人工驗證〕
- [x] 技術：取樣 waiting（等批准）、working、idle 等狀態下的分頁標題前綴——發現 `✳`、`◐` 以外的符號時，回頭修訂規格的狀態前綴清單〔取樣完成：**實測發現 `◑`（U+25D1）**，規格清單需修訂——依長線規則未自行修改 delta.md，交使用者決定〕
- [ ] 技術：所在視窗最小化時能還原並選中分頁；從桌寵點擊觸發時，SetForegroundWindow 能把 WT 帶到前景（不只在工作列閃爍）〔前半已實測通過；後半只驗了代理情境（見驗證證據），桌寵實點需人工確認，故不打勾〕
- [x] 技術：決定要用 `ctypes` 或 `comtypes`（或其他套件）；需要裝新套件時依紅線 6 先查證並回報使用者〔決定：純 `ctypes`，不需新套件〕
- [x] 技術：實驗結論寫進本卡的「實作備註」；實驗腳本放 `scripts/` 或 scratchpad，不進正式程式碼〔腳本放 scratchpad，未進 repo〕

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**：
- 無（實驗卡，沒有新增正式程式碼，故不補測試；標題擷取與分頁比對的純函式測試屬於後續實作卡。既有 52 個測試與 ruff 全綠）

**AI 實際操作驗過**：
- 列分頁（ctypes 直呼 UIAutomationCore COM）：本機 1 個 WT 視窗 → 列出 3 個分頁 `✳ Cladue mod 區塊修改`、`✳ L22401 sklearn 評估與建模筆記`、`◐ Claude Code`，含目前選中哪一個；單視窗約 40～110 ms
- 在 worker thread（且同程序已有 QApplication）中呼叫同一套 ctypes UIA → 正常列出 3 個分頁（約 40 ms），可符合規格「背景處理」設計
- 標題擷取：讀 `~/.claude/projects/*/*.jsonl` 最近 48 小時的 19 個檔，只讀檔尾 1 MB、只解析含 `"ai-title"`／`"custom-title"` 的行 → 14 個有 `ai-title`，最後一筆標題距檔尾 5.8～33.8 KB，每檔 2～21 ms；5 個無標題（含本 session 父對話，其分頁顯示預設名 `Claude Code`）
- 標題 ↔ 分頁比對：`Cladue mod 區塊修改` → 1 個同名分頁 `✳ Cladue mod 區塊修改`；`L22401 sklearn 評估與建模筆記` → 1 個同名分頁；`任務進度條 Phase 4`（無對應分頁）→ 0 個；無標題 → 0 個
- 比對規則反例（用假字串）：`.env` 對 `env`／`✳ env` 不同名；`env` 對 `# env`／`$ env` 不同名；空標題不同名——都符合 delta 名詞定義
- 狀態前綴取樣：背景中 8 秒、40 次取樣只看到 `✳`（閒置分頁）與 `◐`（執行中、分頁未被聚焦）；把 WT 帶到前景並選中執行中的分頁後 3 秒取樣 → 出現 **`◐`、`◑`（U+25D1）**、`✳` 三種
- UIA `SelectionItem.Select` 在 WT 位於背景時選分頁 → 選中成功，**而且 WT 會被一起帶到前景**（連做兩次都是；Select 後 0.05 秒前景即變成 WT）
- 從背景程序（非前景、未收到輸入）直接呼叫 `SetForegroundWindow(WT)` → 回傳 False、WT 沒有變前景；先送一個「位移 0 的滑鼠移動」合成輸入（SendInput）再呼叫 → 回傳 True、WT 成為前景（本機 ForegroundLockTimeout = 2147483647，即鎖定不會逾時）
- 最小化還原：把自己所在的 WT 視窗 `ShowWindow(SW_MINIMIZE)` → IsIconic=True；最小化狀態下 UIA 仍能列出 3 個分頁（105 ms）並 Select 成功；`ShowWindow(SW_RESTORE)` + `SetForegroundWindow` → IsIconic=False、成為前景、選中目標分頁
- 收尾：每次實驗後都選回使用者原本的分頁（`✳ L22401 sklearn 評估與建模筆記`）並把前景還給原視窗（Obsidian），已確認還原成功；沒有關閉任何分頁或視窗

**AI 驗不了、必須人工看的**：
- 從桌寵實際點擊後，`SetForegroundWindow` 能把 WT 帶到前景（不只工作列閃爍）——AI 只能用「合成滑鼠輸入」模擬「本程序剛收到輸入」的條件，桌寵實點需在實作卡完成後人工確認（不涉及金額／日期計算）
- 背景程序呼叫失敗時，WT 是否只在工作列閃爍（AI 看不到畫面）
- `/rename` 改名後分頁標題是否立刻變成新名稱、紀錄檔是否新增 `custom-title` 行（本機紀錄檔沒有任何改名紀錄，子代理也無法執行 slash command）
- waiting（等批准）狀態下的分頁前綴（無法觸發；依程式碼推論為 `✳`）
- 兩個以上 WT 視窗時的行為（本機只開 1 個視窗），包括「最近使用過的 WT 視窗」挑選（AC-JUMP-04、15）

**可能因環境而異的行為**：
- 前景切換受 Windows 前景鎖定規則影響（ForegroundLockTimeout、是否剛有使用者輸入、呼叫程序是否為前景程序的子程序等）；本機實測「子程序在父程序為前景時可切換」「合成輸入後可切換」都成立，其他機器的設定可能不同
- UIA `Select` 會順帶把 WT 帶到前景，這是 WT 自身行為，WT 版本不同可能改變
- `◐`／`◑` 交替只在該分頁「被聚焦」時發生（Claude Code 依終端機焦點回報決定是否播放動畫）；使用者設定 `terminalTitleFromRename: false`、在 tmux 等多工器內、或 Claude Code 開啟「分頁顯示狀態」功能時，前綴與標題來源會不同（見實作備註）
- 不同 Claude Code 版本的前綴字元與標題邏輯可能改變（本次依 2.1.295）

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

### 實驗結論（五個問題）

1. **標題比對**：可行。紀錄檔最後 1 MB 內一定找得到最後一筆標題（實測 19 檔，最遠 33.8 KB），標題與分頁去前綴後完全相同；用位元組先過濾 `"ai-title"`／`"custom-title"` 再 JSON 解析，不必碰對話內容。沒有標題的 session，分頁顯示預設名 `Claude Code`（多個無標題 session 會撞名，但規格已規定「沒有標題就不算同名」，不受影響）。
2. **`/rename`**：會更新分頁標題（**推論**，依 Claude Code 2.1.295 程式碼）：`/rename` 寫入 `{"type":"custom-title","customTitle":...}` 並立即更新目前 session 標題；分頁標題取值順序為「改名標題 → AI 標題 → agent 類型 → 預設 `Claude Code`」。例外：使用者設定 `terminalTitleFromRename: false`（預設 true）時，分頁維持 AI 標題，此時以 custom-title 優先比對會找不到分頁。改名為空字串視同清除改名、回到 AI 標題。→ AC-JUMP-06 不需修訂；`terminalTitleFromRename: false` 是否要處理，交使用者決定。
3. **狀態前綴**：**與規格不同**。程式碼為 `S6=["◐","◑"]`、`b6="✳"`：執行中（busy）且終端機有焦點時，前綴每 960 ms 在 `◐`（U+25D0）與 `◑`（U+25D1）間交替；未聚焦時固定 `◐`；其他狀態（含 waiting 等批准、閒置）都是 `✳`。實測已取樣到 `◑`。另有兩種「無前綴」情況：設定開啟「分頁顯示狀態」（`showStatusInTerminalTab`，實驗中功能）時只顯示標題；在 tmux 等多工器內固定 `✳`。→ **delta.md 的 `STATUS_PREFIXES` 與名詞定義「狀態前綴」需加入 `◑`（U+25D1）**，否則使用者正在看著執行中的那個分頁時，約一半時間會比對失敗。依長線規則未自行修改，待使用者決定。
4. **最小化還原**：可行。最小化時 UIA 仍可列分頁並 Select；`IsIconic` → `ShowWindow(SW_RESTORE)` 後再帶到前景即可。注意只對 `IsIconic` 為真的視窗呼叫 SW_RESTORE（對最大化但未最小化的視窗呼叫會把它縮小成一般大小）。
5. **前景切換**：大致可行，桌寵實點待人工確認。背景程序直接呼叫會被 Windows 拒絕；「本程序剛收到使用者輸入」時會成功（以合成滑鼠輸入模擬），桌寵被點擊正符合這個條件。另發現 UIA `Select` 本身就會把 WT 帶到前景，所以「有同名分頁」的路徑幾乎不依賴 SetForegroundWindow；「找不到／撞名」只帶視窗不選分頁的路徑（AC-JUMP-13～15）才完全依賴 SetForegroundWindow。建議實作順序：還原 → Select → SetForegroundWindow，最後以 `GetForegroundWindow() == hwnd` 判定成功與否（AC-JUMP-19）。不建議用 AttachThreadInput／模擬 Alt 鍵等技巧（Alt 可能觸發其他程式的選單），本次也沒有需要。

### 技術選型

- **純 `ctypes`**，不需 `comtypes`／`pywinauto`（venv 內本來就沒有，未安裝任何套件）。做法：`CoCreateInstance(CLSID_CUIAutomation)` 取得 `IUIAutomation`，以 vtable 索引呼叫方法。用到的索引：IUIAutomation `ElementFromHandle=6`、`CreateTrueCondition=21`；IUIAutomationElement `FindAll=6`、`GetCurrentPattern=16`、`get_CurrentControlType=21`、`get_CurrentName=23`；IUIAutomationElementArray `get_Length=3`、`GetElement=4`；IUIAutomationSelectionItemPattern `Select=3`、`get_CurrentIsSelected=6`（`GetCurrentPattern` 回傳 IUnknown，需 QueryInterface 成 `{A8EFA66A-0FDA-421A-9194-38021F3578EA}`）。TabItem 控制類型 50019、SelectionItem pattern 10010、TreeScope_Descendants=4。名稱是 BSTR，讀完要 `SysFreeString`；每個 COM 指標用完要 Release。worker thread 先 `CoInitializeEx(None, COINIT_MULTITHREADED)`。
- WT 視窗用 `EnumWindows` + `GetClassNameW == "CASCADIA_HOSTING_WINDOW_CLASS"` 找；EnumWindows 依 Z-order（上層在前），可作為「最近使用過的 WT 視窗」的依據（推論，未在多視窗下實測）。
- 實驗腳本（`wt_uia.py`、`titles.py`、`fg_test.py` 等）放在本次對話的 scratchpad，未進 repo；上面的索引與做法已足夠讓實作卡重寫。
