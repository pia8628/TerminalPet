# 04-跳不過去時的提示與保護

**做完能 demo 什麼**：觸發切換但跳不過去時（分頁撞名、沒有標題、找不到分頁、沒有開 WT、假 session、切換失敗或逾時），桌寵旁邊會出現對應的跳轉提示，3 秒後自動消失，能叫出 WT 視窗時盡量叫出來；跳轉處理中再點擊會被忽略，桌寵全程不會卡住。

**Blocked by**：03-右鍵「切換到終端機」

**狀態**：已驗收（2026-10-09）

**檢查點**：否

## 規格依據

- US-JUMP-03
- AC-JUMP-13、AC-JUMP-14、AC-JUMP-15、AC-JUMP-16、AC-JUMP-17、AC-JUMP-18、AC-JUMP-19、AC-JUMP-20、AC-JUMP-21

## 驗收條件

- [x] AC-JUMP-13（錯誤）：Given 兩個分頁都叫 `✳ 寫週報`，`abc123` 標題 `寫週報` → When 觸發切換 → Then WT 移到最前面但分頁選取不變；提示「有 2 個分頁同名，請手動切換」（已實作，以假 Windows API 測試；本機沒有撞名分頁，實機待人工）
- [x] AC-JUMP-14（錯誤）：Given `abc123` 尚未產生標題，有一個 WT 開著 → When 觸發切換 → Then WT 移到最前面但分頁選取不變；提示「找不到這個 session 的分頁」（「WT 移到最前面」在 WT 沒被最小化時，要從桌寵實點才驗得到，待人工）
- [x] AC-JUMP-15（錯誤）：Given `abc123` 有標題但沒有同名分頁，開著兩個 WT → When 觸發切換 → Then 最近使用的 WT 移到最前面，分頁選取不變；提示「找不到這個 session 的分頁」（兩個 WT 視窗的情境本機無法驗，待人工）
- [x] AC-JUMP-16（錯誤）：Given 沒有任何 WT 視窗 → When 觸發切換 → Then 不切換任何視窗；提示「找不到這個 session 的分頁」（以假 Windows API 測試；實機待人工）
- [x] AC-JUMP-17（錯誤）：Given `set_state.py` 寫入的假 session，或紀錄檔已刪除／無法讀取 → When 觸發切換 → Then 比照「沒有標題」處理；桌寵不中止、其他燈照常
- [x] AC-JUMP-18（邊界）：Given 提示正在顯示 → When 3 秒內不做任何事 → Then 提示自動消失；期間拖曳、右鍵、點擊照常可用（「照常可用」的手感待人工）
- [x] AC-JUMP-19（錯誤）：Given 有唯一同名分頁，但分頁在切換前被關閉、選取失敗、前景被 Windows 拒絕、或處理超過 3 秒 → When 觸發切換 → Then 提示「切換失敗，請手動切換」；不會切到其他分頁；逾時後不再開始新的切換動作，也不顯示第二個提示
- [x] AC-JUMP-20（邊界）：Given 一個跳轉正在處理中 → When 再觸發另一個 session 的切換 → Then 第二次被忽略、不出現提示；第一個照常完成
- [x] AC-JUMP-21（邊界）：Given `abc123` 改名為 `.env`，WT 只有 `✳ env`、`PowerShell` → When 觸發切換 → Then 不切到 `✳ env`，依 AC-JUMP-15 處理
- [x] 技術：世代編號＋取消旗標，worker 在每個切換動作開始前都檢查；桌寵關閉時設取消旗標
- [x] 技術：既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**（全部 137 個測試與 ruff 全綠；本卡淨增 31 個，含參數化）：
- `tests/test_wt_jump.py::test_AC_JUMP_03_unique_tab_is_selected_and_brought_front` — 唯一同名：先選分頁再帶前景（動作順序）
- `tests/test_wt_jump.py::test_AC_JUMP_13_duplicate_tabs_bring_window_front_without_selecting` — 撞名：只帶視窗到前面、不選分頁，回報同名數 2
- `tests/test_wt_jump.py::test_AC_JUMP_14_no_title_brings_wt_front_without_selecting` — 沒有標題：叫出 WT、不選分頁
- `tests/test_wt_jump.py::test_AC_JUMP_15_no_match_brings_most_recent_wt_front` — 找不到：叫出 Z-order 最上層（最近使用）的 WT，最小化的先還原
- `tests/test_wt_jump.py::test_AC_JUMP_16_no_wt_window_switches_nothing` — 沒有 WT：不做任何視窗動作
- `tests/test_wt_jump.py::test_AC_JUMP_17_fake_or_missing_transcript_is_treated_as_no_title`、`test_AC_JUMP_17_system_errors_without_title_stay_not_found` — 假 session／紀錄檔已刪 → 比照沒有標題；沒有標題時系統錯誤仍回「找不到」而不是「切換失敗」
- `tests/test_wt_jump.py::test_AC_JUMP_21_dot_env_does_not_switch_to_env_tab` — `.env` 不選 `✳ env`
- `tests/test_wt_jump.py::test_AC_JUMP_19_tab_closed_before_select_fails_without_other_tab`、`test_AC_JUMP_19_foreground_refused_is_failed` — 分頁被關閉／前景被拒 → failed，且不會改切其他分頁
- `tests/test_wt_jump.py::test_AC_JUMP_19_cancel_is_checked_before_every_switch_action`（3 組）、`test_cancel_also_stops_bringing_wt_front` — 取消後不再開始還原／選分頁／帶前景
- `tests/test_pet.py::test_AC_JUMP_13_to_19_hint_text`（9 組）— 結果代碼 → 提示文案（照 delta 原文；ok／unsupported 不提示）
- `tests/test_pet.py::test_AC_JUMP_13_to_19_hint_is_shown_after_failed_jump`（3 組）、`test_AC_JUMP_08_no_hint_on_success_or_unsupported` — 跳轉結束後真的顯示（或不顯示）提示框
- `tests/test_pet.py::test_AC_JUMP_18_hint_disappears_by_itself_and_does_not_block_pet` — 提示自動消失；不接收滑鼠、不搶焦點、非 modal
- `tests/test_pet.py::test_AC_JUMP_20_second_jump_while_busy_is_ignored` — 處理中經 `_jump_to` 再觸發被忽略、第一個照常完成、完成後可再跳
- `tests/test_pet.py::test_AC_JUMP_19_timeout_reports_failed_once_and_cancels_worker` — 逾時回報 failed 一次、worker 看到取消旗標、晚到結果被丟掉
- `tests/test_pet.py::test_AC_JUMP_19_late_result_of_old_jump_does_not_leak_into_new_jump` — 舊跳轉晚到的結果不會被當成新跳轉的結果（世代編號）
- `tests/test_pet.py::test_closing_pet_sets_cancel_flag` — 桌寵關閉（`aboutToQuit`）設取消旗標、不再回報
- 反向確認（暫時改壞程式、確認測試變紅後還原，已用 `cmp` 確認檔案還原）：拿掉兩層「處理中忽略」→ AC_JUMP_20 紅；拿掉世代編號檢查 → 3 個逾時／關閉測試紅；拿掉 worker 的取消檢查 → 4 個取消測試紅；關閉時不設取消旗標 → `test_closing_pet_sets_cancel_flag` 紅；找不到時不叫出 WT → AC_JUMP_15 紅；提示不自動消失 → AC_JUMP_18 紅

**AI 實際操作驗過**（scratchpad 腳本：桌寵的 session／設定資料夾全指向暫存資料夾；在 Windows 真實平台建出 `PetWindow`（非 offscreen），呼叫 `_jump_to`；本機 1 個 WT 視窗，分頁 `◑ Cladue mod 區塊修改`（原本選中）、`✳ iPAS AI 中級戰情室`、`◐ 先行執行的後果`；原本前景是 Obsidian）：
- AC-JUMP-17：transcript 空字串、檔案不存在 → `no_title`，提示框可見、文字「找不到這個 session 的分頁」，選中分頁不變，桌寵照常
- AC-JUMP-15：標題 `不存在的分頁標題` → `no_match`、同上提示、選中分頁不變
- AC-JUMP-21（類比）：標題是現有分頁去前綴後前面加一個點（`.iPAS AI 中級戰情室`）→ `no_match`、沒有切到那個分頁
- AC-JUMP-14：先把 WT 最小化，再觸發沒有標題的跳轉 → WT 還原（IsIconic=False）且成為前景、選中分頁不變、出現「找不到」提示
- AC-JUMP-19 逾時：真的 `jump_to_session` 前面先卡 3.3 秒、目標是未選中的分頁 → 3.03 秒時出現「切換失敗，請手動切換」；再等 0.8 秒（worker 已跑完）仍只有 1 個結果、提示文字沒變、**選中分頁沒有被切走**（逾時後沒有開始切換動作）
- AC-JUMP-20：第一個跳轉處理中再呼叫 `_jump_to("second")` → 背景只收到 `first`、只回報 1 個結果
- AC-JUMP-18：提示在顯示約 3 秒後自動消失
- 提示框位置：桌寵 (1200,600,126×126) → 提示框 (1176,564,172×30)，在桌寵正上方水平置中；**提示框出現後前景都不是提示框**（不搶前景）
- 不卡桌寵：`_jump_to` 立即返回（<0.1 ms）；處理期間主執行緒事件迴圈最大間隔 16 ms，唯一例外是程序第一次跳轉時 141 ms（第一次載入系統 DLL 函式）
- 收尾：選回原本的 `Cladue mod 區塊修改` 分頁，前景已回到原本的 Obsidian 視窗、WT 未最小化；沒有關閉任何分頁或視窗，沒有碰 `~/.terminalpet/`
- 架構檢查：`grep -n "write_text\|open(.*w" pet.py` 只出現 `CONFIG_FILE`；`grep -n PySide6 set_state.py scripts/pet-state.sh wt_jump.py` 無結果

**AI 驗不了、必須人工看的**：
- 從桌寵實際操作（右鍵 →「切換到終端機」）跳不過去時，WT 真的被帶到最前面（不只工作列閃爍）——AI 從背景程序呼叫時 Windows 拒絕切前景（只有「WT 原本最小化、被還原」時會順帶成為前景），桌寵被使用者點擊時才有前景權（不涉及金額／日期計算）
- AC-JUMP-13 實機：開兩個同名分頁（例如兩個 session 用 `/rename` 改成同一個名字），提示「有 2 個分頁同名，請手動切換」且分頁選取不變（本機沒有撞名分頁，AI 沒有開新分頁）
- AC-JUMP-15 兩個 WT 視窗：叫出的是「最近使用過的」那個（本機只有 1 個 WT 視窗；Z-order＝最近使用是推論）
- AC-JUMP-16 實機：關掉所有 WT 後觸發，不切換任何視窗、出現提示
- 提示框外觀：大小、字體、顏色、深色底在各種桌布上是否讀得到；桌寵靠近螢幕上緣時改放下方是否正常
- AC-JUMP-18 期間的手感：提示顯示中拖曳桌寵（提示會跟著移動）、右鍵、點擊都照常
- AC-JUMP-19 的「選取失敗」「分頁在切換前被關閉」「前景被拒（只閃工作列）」實機情境（AI 只用假 API 測）
- 系統匣右鍵選單觸發的跳轉也會在桌寵旁出現提示

**人工驗收結果（2026-10-09）**：
- 使用者 2026-10-09 於 Hub 匯出：4 項全部略過——提示框外觀、位置、3 秒消失尚無人工目視（程式與測試已驗）

**可能因環境而異的行為**：
- 前景切換受 Windows 前景鎖定規則影響：「找不到／撞名」只帶視窗不選分頁，完全依賴 `SetForegroundWindow`（有同名分頁時 UIA `Select` 會順帶把 WT 帶到前景）；某些機器設定可能只讓工作列閃爍
- 「最近使用的 WT」取 `EnumWindows` 的 Z-order 第一個；若 WT 有隱藏視窗（例如縮到系統匣的設定），可能會挑到看不見的視窗
- 第一次跳轉會多約 0.1 秒載入系統函式（只發生一次）

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

- `wt_jump.jump_to_session(transcript, cancelled=None)`：新增 `cancelled` 參數（無參數函式，回 True 表示已逾時／桌寵關閉）。`_switch` 在還原、Select、SetForegroundWindow 每一步前檢查，取消就回 `failed`；新增 `_bring_to_front`（取消檢查 → IsIconic 才還原 → 取消檢查 → SetForegroundWindow，不判定成敗）
- 叫出哪個 WT：沒有標題、`no_match` → `wt_windows()[0]`（Z-order 最上層）；`ambiguous` → 含同名分頁的視窗中 Z-order 最上層者；沒有 WT 視窗 → 不動。沒有標題時不建 UI Automation（只列視窗）
- 沒有標題時若列視窗發生系統錯誤，仍回 `no_title`（提示「找不到」），只有有標題時的錯誤才算 `failed`
- `pet.JumpRunner`：`busy` 屬性；`start()` 處理中回 False；世代編號＋`threading.Event` 取消旗標，worker 拿到的 `cancelled()` 同時檢查旗標與世代編號；主執行緒 `QTimer` 計時 `JUMP_TIMEOUT_MS`（3000），逾時 → `cancel()` 並發出 `failed`；worker 結果經內部 signal `_done(世代, 結果)` 回主執行緒，世代不是進行中的就丟掉。`cancel()` 由 `QApplication.aboutToQuit` 呼叫（桌寵關閉）
- `pet.jump_hint_text(result)` 決定文案；`pet.JumpHint(QLabel)` 是提示框（Qt.ToolTip 視窗、`WA_ShowWithoutActivating`、`WindowDoesNotAcceptFocus`、`WA_TransparentForMouseEvents`），放桌寵正上方、上方放不下改下方並夾在螢幕內，`HINT_MS`（3000）後自動隱藏；再次顯示會重新計時；桌寵移動時提示跟著走（`PetWindow.moveEvent`）
- 給 05、06 卡：左鍵點圓點／列／小狼一律呼叫 `PetWindow._jump_to(session.transcript)`，就會自動套用「處理中忽略」、逾時、提示，不需要另外處理

