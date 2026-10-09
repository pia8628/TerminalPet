# 點擊跳到終端機 變更規格（delta）

> 狀態：草稿 → 已核准 → 實作中 → 已驗收 → 已合併
> 建立日期：2026-10-09
>
> 編號沿用 SPEC.md 的規則：`US-代號-NN`、`AC-代號-NN`，**接在 SPEC.md 該模組現有編號之後往下編**，不重用、不重排。新模組先在 SPEC.md 不存在也沒關係，合併時會新建一節。

**狀態**：實作中（2026-10-09 核准、拆卡）

## 目標

同時在同一個 Windows Terminal 視窗開多個分頁跑 Claude Code 時，點桌寵上的燈就能直接切到那個 session 所在的分頁，不必逐一翻找。

## 新增

### 名詞定義

- **session 標題**：Claude Code 為該 session 取的名稱（也就是 Windows Terminal 分頁上顯示的那段文字）。使用者用 `/rename` 改過名稱時，以最後一次改的名稱為準；沒改過則以 Claude Code 最後一次自動產生的標題為準。只看對話紀錄檔**最後 1 MB** 的內容（Claude Code 會在對話中反覆寫入標題，2026-10-09 實測本機最大 18 MB 的紀錄檔，最後一筆標題距檔尾不到 30 KB）；這段內容裡找不到任何標題時，該 session「沒有標題」。
- **狀態前綴**：Claude Code 加在分頁標題最前面、表示狀態的「一個狀態符號＋一個空白」。狀態符號只認明確清單：`✳`（U+2733，閒置）、`◐`（U+25D0，執行中）、`◑`（U+25D1，執行中；分頁被聚焦時與 `◐` 約每秒交替），為 2026-10-09 以 UI Automation 對本機 WT 分頁取樣所得（`◑` 為 01 卡可行性實驗補充，使用者 2026-10-09 核准）。清單以外的字元一律不視為狀態前綴。session 標題本身**不做任何改寫**，只去掉頭尾空白。
- **分頁比對**：分頁標題與 session 標題**完全相同**，或分頁標題恰好等於「一個狀態前綴＋session 標題」，才算同名分頁（區分大小寫）。session 標題為空時不算同名。例：session 標題 `任務進度條 Phase 4` 與分頁 `✳ 任務進度條 Phase 4`、`◐ 任務進度條 Phase 4`、`◑ 任務進度條 Phase 4`、`任務進度條 Phase 4` 都同名；session 標題 `.env` 與分頁 `env`、`✳ env` 都不同名；session 標題 `env` 與分頁 `# env`、`$ env` 都不同名。比對範圍是目前所有 Windows Terminal 視窗的所有分頁。
- **點一下**：左鍵按下到放開之間，滑鼠移動距離未超過系統的拖曳門檻（Windows 預設約 4 px）。超過門檻才算拖曳。
- **跳轉提示**：桌寵旁邊出現的一個小提示框，3 秒後自動消失，不需要按任何按鈕。
- **跳轉處理不卡桌寵**：從點擊到切換完成（或失敗）的整個處理在背景進行；處理期間桌寵的燈號更新、閃燈、拖曳、右鍵都照常運作。處理超過 3 秒仍未完成，視為切換失敗（見 AC-JUMP-19）。同一時間只處理一個跳轉，處理中再點擊會被忽略。
  - **逾時後的保證範圍**：處理分兩段——「查找」（讀標題、列出分頁）與「切換」（還原視窗、選分頁、帶到最前面，每一步都是一個動作）。逾時或桌寵關閉之後，**不會再開始任何新的切換動作**；但逾時當下已經在執行中的那一個動作無法中斷，可能在提示出現後才完成。這個晚到的動作只會作用在已比對到的那個同名分頁或其視窗上，不會切到其他分頁。此為已知限制，於規格核准時向使用者說明。

### User Stories

- **US-JUMP-01**：身為在同一個 WT 視窗開多個分頁的使用者，我要點某個 session 的燈或清單列就切到它的分頁，才能不必逐一翻分頁找
- **US-JUMP-02**：身為看到紅燈的使用者，我要點小狼就直接跳到最需要我的 session，才能最快處理
- **US-JUMP-03**：身為使用者，我要跳不過去時有清楚的提示並盡量幫我把終端機叫出來，才能知道接下來要手動做什麼
- **US-HOOK-04**：身為使用者，我要每個 session 的狀態檔記下它的對話紀錄檔位置，才能讓桌寵找得到 session 標題

### 行為規則（驗收情境）

- **AC-JUMP-01**（US-JUMP-01，成功）
  - Given：Windows，一個 WT 視窗有 3 個分頁，標題為 `✳ 寫週報`、`✳ 任務進度條 Phase 4`、`PowerShell`；目前選中第 1 個分頁；session `abc123` 的標題為 `任務進度條 Phase 4`；外觀為紅綠燈版
  - When：左鍵點一下 `abc123` 的小圓點
  - Then：WT 視窗移到最前面，選中的分頁變成第 2 個（`✳ 任務進度條 Phase 4`）；桌寵位置不變，不出現跳轉提示
- **AC-JUMP-02**（US-JUMP-01，成功）
  - Given：同 AC-JUMP-01，但已開啟「顯示專案名稱」
  - When：左鍵點一下 `abc123` 那一列（圓點或文字皆可）
  - Then：與 AC-JUMP-01 相同，切到第 2 個分頁
- **AC-JUMP-03**（US-JUMP-01，成功）
  - Given：同 AC-JUMP-01
  - When：右鍵 → `abc123` 的子選單 →「切換到終端機」
  - Then：與 AC-JUMP-01 相同，切到第 2 個分頁
- **AC-JUMP-04**（US-JUMP-01，邊界）
  - Given：session `abc123` 標題為 `任務進度條 Phase 4`；它所在的 WT 視窗已最小化；另有第二個 WT 視窗在最前面
  - When：點一下 `abc123` 的小圓點
  - Then：第一個 WT 視窗還原並移到最前面，選中標題為 `✳ 任務進度條 Phase 4` 的分頁；第二個 WT 視窗的分頁選取不變
- **AC-JUMP-05**（US-JUMP-01，邊界）
  - Given：session `abc123` 正在執行中，分頁標題顯示為 `◐ 任務進度條 Phase 4`
  - When：點一下 `abc123` 的小圓點
  - Then：仍判定為同名分頁並切過去；分頁標題顯示為 `◑ 任務進度條 Phase 4` 時亦同
- **AC-JUMP-06**（US-JUMP-01，邊界）
  - Given：session `abc123` 的自動標題原為 `任務進度條 Phase 4`，使用者之後以 `/rename` 改名為 `跳轉功能`，分頁標題顯示 `✳ 跳轉功能`
  - When：點一下 `abc123` 的小圓點
  - Then：切到 `✳ 跳轉功能` 那個分頁
- **AC-JUMP-07**（US-JUMP-01，邊界）
  - Given：桌寵在螢幕上，滑鼠左鍵按在某 session 的小圓點上
  - When：拖動 30 px 後放開
  - Then：視為拖曳：桌寵移到新位置並記住位置，不切換分頁
- **AC-JUMP-08**（US-JUMP-01，邊界）
  - Given：非 Windows 系統，有一個 session
  - When：左鍵點一下它的小圓點，或對桌寵按右鍵開啟它的子選單
  - Then：點擊沒有任何反應、不出現跳轉提示；子選單中沒有「切換到終端機」這一項
- **AC-JUMP-09**（US-JUMP-02，成功）
  - Given：外觀為動物版，三個 session：A（working，首次出現 100）、B（waiting，首次出現 200）、C（waiting，首次出現 300），三者都有對應的同名分頁
  - When：左鍵點一下小狼
  - Then：切到 B 的分頁（狀態最需要注意者中首次出現最早的）
- **AC-JUMP-10**（US-JUMP-02，成功）
  - Given：外觀為動物版，兩個 session：A（thinking，首次出現 100）、B（done，首次出現 200）
  - When：左鍵點一下小狼
  - Then：切到 B 的分頁（依 waiting → done → working → thinking 的順序找第一個有 session 的狀態）
- **AC-JUMP-11**（US-JUMP-02，邊界）
  - Given：外觀為動物版，所有 session 都顯示為 idle（含逾時轉 idle 者），或沒有任何 session
  - When：左鍵點一下小狼
  - Then：沒有任何反應：不切換視窗、不出現跳轉提示
- **AC-JUMP-12**（US-JUMP-02，邊界）
  - Given：外觀為紅綠燈版，沒有任何 session，只顯示 1 顆灰色圓點
  - When：左鍵點一下那顆灰點
  - Then：沒有任何反應
- **AC-JUMP-13**（US-JUMP-03，錯誤）
  - Given：一個 WT 視窗有兩個分頁標題都是 `✳ 寫週報`；session `abc123` 標題為 `寫週報`
  - When：點一下 `abc123` 的小圓點
  - Then：WT 視窗移到最前面但選中的分頁不變；跳轉提示顯示「有 2 個分頁同名，請手動切換」
- **AC-JUMP-14**（US-JUMP-03，錯誤）
  - Given：session `abc123` 剛開啟、尚未產生標題；有一個 WT 視窗開著
  - When：點一下 `abc123` 的小圓點
  - Then：WT 視窗移到最前面但選中的分頁不變；跳轉提示顯示「找不到這個 session 的分頁」
- **AC-JUMP-15**（US-JUMP-03，錯誤）
  - Given：session `abc123` 標題為 `寫週報`，但沒有任何 WT 分頁同名（例如它跑在 VS Code 的終端機，或分頁已關閉）；開著兩個 WT 視窗
  - When：點一下 `abc123` 的小圓點
  - Then：最近使用過的那個 WT 視窗移到最前面，分頁選取不變；跳轉提示顯示「找不到這個 session 的分頁」
- **AC-JUMP-16**（US-JUMP-03，錯誤）
  - Given：沒有任何 WT 視窗開著；session `abc123` 有標題
  - When：點一下 `abc123` 的小圓點
  - Then：不切換任何視窗；跳轉提示顯示「找不到這個 session 的分頁」
- **AC-JUMP-17**（US-JUMP-03，錯誤）
  - Given：session 是用 `set_state.py` 寫入的假 session（沒有對話紀錄檔），或其對話紀錄檔已被刪除或無法讀取
  - When：點一下它的小圓點
  - Then：比照「沒有標題」處理（同 AC-JUMP-14／AC-JUMP-16）；桌寵不中止、其他燈照常顯示
- **AC-JUMP-18**（US-JUMP-03，邊界）
  - Given：跳轉提示正在顯示「找不到這個 session 的分頁」
  - When：3 秒內不做任何事
  - Then：提示自動消失；期間桌寵的拖曳、右鍵、點擊都照常可用
- **AC-JUMP-19**（US-JUMP-03，錯誤）
  - Given：session `abc123` 有唯一的同名分頁，但切換時發生以下任一情況：該分頁在切換前被關閉、選取分頁的動作失敗、Windows 拒絕把 WT 視窗帶到最前面（例如只在工作列閃爍）、整個處理超過 3 秒
  - When：點一下 `abc123` 的小圓點
  - Then：跳轉提示顯示「切換失敗，請手動切換」；桌寵不中止，燈號與其他操作照常；不會切到其他分頁
- **AC-JUMP-20**（US-JUMP-03，邊界）
  - Given：一個跳轉正在處理中（尚未完成或失敗）
  - When：再點一下另一個 session 的小圓點
  - Then：第二次點擊被忽略，不出現提示；第一個跳轉照常完成
- **AC-JUMP-21**（US-JUMP-01，邊界）
  - Given：session `abc123` 以 `/rename` 改名為 `.env`；WT 只有兩個分頁，標題為 `✳ env`、`PowerShell`
  - When：點一下 `abc123` 的小圓點
  - Then：不切到 `✳ env`；視為找不到同名分頁，依 AC-JUMP-15 處理
- **AC-HOOK-15**（US-HOOK-04，成功）
  - Given：hook 資料帶有對話紀錄檔路徑 `C:\Users\me\.claude\projects\D--Projects-TerminalPet\abc123.jsonl`
  - When：觸發任一會寫入狀態的事件
  - Then：狀態檔多一個紀錄檔路徑欄位，值為 `C:/Users/me/.claude/projects/D--Projects-TerminalPet/abc123.jsonl`（反斜線轉正斜線）；其他欄位與既有行為（AC-HOOK-09～14）相同
- **AC-HOOK-16**（US-HOOK-04，邊界）
  - Given：hook 資料沒有對話紀錄檔路徑（例如手動執行寫入端）
  - When：觸發會寫入狀態的事件
  - Then：紀錄檔路徑欄位為空字串，狀態照常寫入

## 修改

- **原本**（SPEC.md AC-OPS-04）：Given 桌寵在螢幕上；When 左鍵點一下但沒有移動就放開；Then 不更新記住的位置
  **改為**：Given 桌寵在螢幕上；When 左鍵點一下（移動未超過拖曳門檻）就放開；Then 不更新記住的位置、桌寵不移動；點的位置在 session 圓點、清單列或小狼上時，依 AC-JUMP-01、02、09～12 跳轉，點在其他位置則沒有任何反應
  **影響檢查**：AC-OPS-01（拖曳記位置）只在超過門檻時觸發，行為不變，見 AC-JUMP-07；AC-OPS-03（往左上長）與點擊無關；AC-VIEW-09～11（閃燈、滑鼠停留提示）不受點擊影響
- **原本**（SPEC.md AC-OPS-05）：每個 session 一個子選單（標題含狀態圓點與「名稱  狀態 經過時間」；子選單有「開啟資料夾」〔僅有路徑時〕與「從清單移除」）……
  **改為**：每個 session 一個子選單（標題同前；子選單依序為「切換到終端機」〔僅 Windows〕、「開啟資料夾」〔僅有路徑時〕、「從清單移除」）；其餘選單項目與順序不變
  **影響檢查**：AC-OPS-06（沒有 session 時無子選單）不變；AC-OPS-07（從清單移除）行為不變；AC-NOTI-03（系統匣右鍵選單與桌寵相同）會同步出現新項目，視為預期
- **原本**（SPEC.md 全域規則「單向資料流」）：Claude Code hooks 寫入每個 session 的狀態檔；桌寵只讀取與顯示，只會刪除狀態檔，不會建立或改寫狀態檔
  **改為**：原條文不變，另加一句：「桌寵可唯讀 Claude Code 的對話紀錄檔，但只取 session 標題，不讀取對話內容，也不寫入紀錄檔」
  **影響檢查**：HOOK 模組仍是狀態檔唯一寫入者；SESS 模組的逾時與清除（AC-SESS-01～08）只看狀態檔，不受紀錄檔影響
- **原本**（SPEC.md Out of Scope；狀態來源見 AC-HOOK-01～14）：用 hooks 以外的方式偵測狀態（讀終端機畫面、解析 log）；點子池含「點擊燈號跳到對應終端機視窗」
  **改為**：用 hooks 以外的方式偵測**狀態**（讀終端機畫面、解析對話內容）；例外：為了跳轉，可唯讀對話紀錄檔中的 session 標題。點子池移除「點擊燈號跳到對應終端機視窗」
  **影響檢查**：狀態判定仍只來自 hooks（事件與狀態對應表不變）；`專案計劃.md` 第四節同步修改同一句

## 移除

- 無

## Implementation Decisions（實作決策，簡記）

- 寫入端：`pet-state.sh` 從 hook stdin 取 `transcript_path`，比照 `cwd` 轉正斜線後寫入狀態檔新欄位 `transcript`；`set_state.py` 寫空字串。仍只用 bash 內建指令。
- 標題來源：只讀 `transcript` 檔（JSONL）最後 1 MB（切掉第一行殘段），取最後一筆改名紀錄；沒有則取最後一筆 `type: ai-title` 的 `aiTitle`。只在點擊當下於背景執行緒讀，不輪詢。改名紀錄的格式見下方「改名紀錄格式」。
- 改名紀錄格式：`{"type":"custom-title","customTitle":"<名稱>","sessionId":"<sid>"}`，2026-10-09 從本機安裝的 Claude Code 程式碼確認（`/rename` 寫入此行，且 session metadata 重寫時會與 `ai-title` 一起反覆追加，故落在檔尾 1 MB 內）。分頁標題在改名後是否顯示新名稱，列入第一張卡的可行性實驗；若不顯示，AC-JUMP-06 改為「以自動標題比對」並回頭修訂本規格。
- 分頁比對：`STATUS_PREFIXES = ("✳ ", "◐ ", "◑ ")`；`tab == title or any(tab == p + title for p in STATUS_PREFIXES)`。可行性實驗要再取樣 waiting（等批准）等其他狀態下的分頁標題；發現清單外的狀態符號時，回頭修訂本規格的狀態前綴清單後才實作。
- 背景處理：讀檔＋UI Automation 放在 worker thread，結果用 Qt signal 回到主執行緒顯示提示；3 秒逾時由主執行緒計時。每次跳轉帶一個世代編號（generation）與取消旗標；主執行緒逾時或桌寵關閉時設定取消旗標，worker 在**每一個**切換動作（還原、Select、SetForegroundWindow）開始前檢查旗標與世代編號，不符即放棄；worker 回報結果時世代編號不符（已逾時）則主執行緒丟棄結果、不再顯示第二個提示。worker 設為 daemon thread，不阻擋桌寵關閉。
- 分頁定位：Windows UI Automation（找 class `CASCADIA_HOSTING_WINDOW_CLASS` 視窗底下的 TabItem，比對名稱後 Select），視窗以 Win32 API 還原並帶到前景。2026-10-09 已實測可列出分頁名稱與 RuntimeId。用 `ctypes`／`comtypes` 或 PySide6 現有能力實作，新增套件須依紅線 6 先查證。
- 前景切換：Windows 對「把別的程式帶到前景」有限制（SetForegroundWindow），使用者點擊桌寵時桌寵擁有前景權，通常可行；可行性實驗須確認。
- 點擊判定：改用 `QApplication.startDragDistance()` 當拖曳門檻。
- 第一張卡為可行性實驗（標題比對、`/rename`、狀態前綴字元、最小化還原、前景切換），失敗則回頭修改本規格。
- `CLAUDE.md` 架構表的「顯示端」職責需補一句「可唯讀對話紀錄檔的標題」，`grep` 檢查方式不變（pet.py 仍只寫 `CONFIG_FILE`）。

## Testing Decisions

- 只測外部行為，不測實作細節
- 要測的重點：
  - AC-HOOK-15、16：延伸 `tests/test_pet_state.py`
  - 標題擷取（custom-title 優先、無標題、檔案不存在）與分頁比對規則（去狀態符號、完全相同、撞名數量）寫成純函式，用假資料測試，對應 AC-JUMP-05、06、13、14、17、21
  - 小狼挑選目標 session 的規則（AC-JUMP-09～11）寫成純函式測試
  - 實際切換視窗／分頁（AC-JUMP-01～04、07、15、16、18～20）無法在 CI 自動測，列入人工驗收
- 既有測試可參考：`tests/test_pet_state.py`、`tests/test_pet.py`

## Out of Scope（這次不做）

- 互動時記下分頁識別碼（方案 A）、從桌寵開新 Claude 分頁（方案 C）
- VS Code 等 Windows Terminal 以外的終端機
- 在桌寵上顯示 session 標題
- 分割窗格（split pane）中切到特定窗格（只切到分頁）
- 簡易進度顯示（另開 change）
- 使用者把 Claude Code 設定 `terminalTitleFromRename` 改為 `false`（改名後分頁維持自動標題）時的比對；預設為 `true`（01 卡實驗發現，使用者 2026-10-09 決定這次不做）

<!-- codex-peer-reviewed: 2026-10-09T04:19:58Z rounds=6 verdict=approved -->
