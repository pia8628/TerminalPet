# 03-右鍵「切換到終端機」（成功路徑）

**做完能 demo 什麼**：在 Windows 上對桌寵按右鍵 → 某個 session 的子選單 →「切換到終端機」，WT 視窗就會移到最前面並選中同名分頁；分頁標題帶 `✳`／`◐` 前綴、用 `/rename` 改過名、所在視窗已最小化都能正確切換。非 Windows 系統的子選單不會出現這一項。

**Blocked by**：01-可行性實驗、02-寫入端記錄對話紀錄檔路徑

**狀態**：已驗收（2026-10-09）

**檢查點**：是（核心流程：標題擷取、分頁比對、背景切換機制，04、05 都蓋在它上面）

## 規格依據

- US-JUMP-01
- AC-JUMP-03、AC-JUMP-04、AC-JUMP-05、AC-JUMP-06、AC-JUMP-08（選單部分）
- 修改後的 AC-OPS-05（子選單依序為「切換到終端機」〔僅 Windows〕、「開啟資料夾」、「從清單移除」）

## 驗收條件

- [x] AC-JUMP-03（成功）：Given 一個 WT 視窗有 `✳ 寫週報`、`✳ 任務進度條 Phase 4`、`PowerShell` 三個分頁，目前選中第 1 個；`abc123` 標題為 `任務進度條 Phase 4` → When 右鍵 → `abc123` 子選單 →「切換到終端機」 → Then WT 移到最前面，選中第 2 個分頁〔AI 以假 session＋本機真實紀錄檔、從選單動作觸發實測；「右鍵實際點選」需人工〕
- [ ] AC-JUMP-04（邊界）：Given `abc123` 所在的 WT 視窗已最小化，另一個 WT 視窗在最前面 → When 觸發切換 → Then 第一個視窗還原並移到最前面、選中同名分頁；第二個視窗的分頁選取不變〔不打勾：單一視窗的「最小化 → 還原、選中、成為前景」已實測通過；本機只有 1 個 WT 視窗，「另一個 WT 視窗在最前面、其分頁不變」需人工〕
- [x] AC-JUMP-05（邊界）：Given 分頁標題為 `◐ 任務進度條 Phase 4` → When 觸發切換 → Then 仍判定為同名分頁並切過去
- [x] AC-JUMP-06（邊界）：Given 自動標題原為 `任務進度條 Phase 4`、之後以 `/rename` 改名為 `跳轉功能` → When 觸發切換 → Then 切到 `✳ 跳轉功能`（依 01 卡的實驗結論，必要時已修訂此 AC）〔AI 以假紀錄檔（ai-title 舊標題＋custom-title 新名稱）實測切到同名分頁；真的 `/rename` 後的分頁需人工〕
- [x] AC-JUMP-08（邊界，選單部分）：Given 非 Windows 系統 → When 開啟 session 子選單 → Then 沒有「切換到終端機」這一項〔以測試模擬非 Windows；實機非 Windows 未測〕
- [x] AC-OPS-05（修改）：子選單順序為「切換到終端機」→「開啟資料夾」（僅有路徑時）→「從清單移除」；系統匣選單同步出現新項目〔系統匣與桌寵共用同一個建選單函式；系統匣實際右鍵畫面需人工〕
- [x] 技術：標題擷取（`custom-title` 優先、無標題、檔案不存在）與分頁比對（狀態前綴、完全相同、撞名數量）寫成純函式，用假資料寫進 `tests/`
- [x] 技術：讀檔＋UI Automation 放在背景執行緒（daemon），結果用 Qt signal 回主執行緒；處理中桌寵燈號、拖曳、右鍵照常運作〔以「背景處理期間主執行緒計時器持續跳動」驗證事件迴圈不被卡住；實際拖曳／右鍵手感需人工〕
- [x] 技術：Windows 專用程式碼放新模組 `wt_jump.py`（顯示端，只讀不寫）；`pet.py` 仍只寫 `CONFIG_FILE`
- [x] 技術：`CLAUDE.md` 架構表「顯示端」職責補一句「可唯讀對話紀錄檔的標題」；`專案計劃.md` 第四節的 Out of Scope 同步修改〔`專案計劃.md` 第四節在規格 commit 3d1bb01 已改好（「不提供 hooks 以外的方式偵測**狀態**……例外：為了點擊跳到終端機……」、點子池已移除該項），本卡核對後無需再改〕
- [x] 技術：既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**（全部 106 個測試與 ruff 全綠；本卡新增 44 個）：
- `tests/test_wt_jump.py::test_AC_JUMP_06_custom_title_overrides_later_ai_title`、`test_AC_JUMP_06_last_custom_title_wins`、`test_empty_custom_title_falls_back_to_ai_title`、`test_last_ai_title_wins`、`test_title_is_only_stripped_not_rewritten` — 標題規則（改名優先、空改名退回自動標題、只去頭尾空白）
- `tests/test_wt_jump.py::test_AC_JUMP_14_no_title_lines_means_no_title`、`test_title_mentioned_in_chat_content_is_ignored`、`test_broken_lines_are_skipped` — 沒有標題、對話內容裡像標題的字不算、壞行略過
- `tests/test_wt_jump.py::test_AC_JUMP_17_missing_transcript_means_no_title`、`test_AC_JUMP_17_unreadable_transcript_means_no_title`、`test_read_session_title_from_file` — 無路徑／檔案不存在／讀不到 → 沒有標題、不丟例外
- `tests/test_wt_jump.py::test_title_before_last_1mb_is_ignored`、`test_title_inside_last_1mb_is_found`、`test_partial_first_line_of_tail_is_dropped`、`test_small_file_is_read_whole` — 只讀最後 1 MB、切掉第一行殘段
- `tests/test_wt_jump.py::test_AC_JUMP_05_status_prefixes_match`（4 組）、`test_AC_JUMP_21_not_same_tab`（11 組）、`test_AC_JUMP_03_finds_the_second_tab`、`test_AC_JUMP_06_renamed_title_finds_renamed_tab`、`test_AC_JUMP_13_duplicate_tabs_are_counted` — 分頁比對（`✳`／`◐`／`◑` 前綴、完全相同、`.env` 不等於 `env`、`# env`／`$ env` 不算、區分大小寫、撞名數量）
- `tests/test_wt_jump.py::test_AC_JUMP_08_non_windows_is_unsupported`、`test_AC_JUMP_17_no_title_does_not_touch_windows`、`test_title_is_passed_to_window_search`、`test_system_errors_become_failed_result` — 主流程分流：非 Windows、沒有標題時不碰視窗、系統錯誤轉成 failed
- `tests/test_pet.py::test_session_reads_transcript_path` — 狀態檔的 `transcript` 欄位讀進 session；舊版狀態檔沒有此欄位時為空字串
- `tests/test_pet.py::test_AC_OPS_05_session_submenu_order` — 子選單順序「切換到終端機 → 開啟資料夾（有路徑才有）→ 從清單移除」
- `tests/test_pet.py::test_AC_JUMP_08_no_switch_item_on_non_windows` — 非 Windows 沒有「切換到終端機」
- `tests/test_pet.py::test_AC_JUMP_03_switch_item_jumps_with_that_sessions_transcript` — 點某 session 的「切換到終端機」帶的是該 session 自己的紀錄檔路徑
- `tests/test_pet.py::test_jump_runs_in_background_and_result_returns_on_main_thread`、`test_jump_errors_are_reported_not_raised` — 跳轉在背景執行緒跑、結果回主執行緒、處理中主執行緒計時器照跑；背景錯誤轉成 failed 回報
- 反向確認（暫時改壞程式、確認測試變紅後還原）：拿掉「切掉第一行殘段」→ `test_partial_first_line_of_tail_is_dropped` 紅；改成自動標題優先 → 3 個 AC-JUMP-06 相關測試紅；比對改成「結尾相同即可」→ `test_AC_JUMP_21_not_same_tab` 4 組紅；拿掉「僅 Windows」判斷 → `test_AC_JUMP_08_no_switch_item_on_non_windows` 紅；改成在主執行緒同步執行 → `test_jump_runs_in_background_and_result_returns_on_main_thread` 紅

**AI 實際操作驗過**（scratchpad 腳本：桌寵的 session／設定資料夾全部指向暫存資料夾，建立 3 個假 session；建出真的 `PetWindow` 與右鍵選單，對子選單「切換到終端機」動作呼叫 `trigger()`；本機 1 個 WT 視窗，分頁為 `✳ Cladue mod 區塊修改`、`✳ iPAS AI 中級戰情室`（原本選中）、`◐ Claude Code`）：
- 選單內容：每個 session 子選單為 `['切換到終端機', '開啟資料夾', '從清單移除']`；頂層選單其餘項目與順序不變
- AC-JUMP-03：假 session 的 transcript 指向本機真實紀錄檔（標題 `Cladue mod 區塊修改`）→ 結果 `ok`、選中分頁變成 `✳ Cladue mod 區塊修改`、前景是 WT；`trigger()` 0.3～2.3 ms 就返回，整個跳轉 73～114 ms，期間主執行緒 5 ms 計時器跳了 14～21 次，結果在主執行緒收到
- AC-JUMP-06：先選中 `✳ Cladue mod 區塊修改`，假紀錄檔內容為「ai-title 舊的自動標題 → custom-title `iPAS AI 中級戰情室` → ai-title 舊的自動標題」→ 結果 `ok`、選中 `✳ iPAS AI 中級戰情室`、前景是 WT
- AC-JUMP-05：假紀錄檔 ai-title `Claude Code` → 切到 `◐ Claude Code`（執行中前綴），結果 `ok`、前景是 WT
- AC-JUMP-04（單視窗部分）：把 WT 視窗最小化（IsIconic=True）後觸發 → 結果 `ok`、IsIconic=False、選中 `✳ Cladue mod 區塊修改`、前景是 WT（總耗時 141～225 ms）
- 找不到時不動任何視窗：transcript 為空、檔案不存在 → `no_title`；標題 `不存在的分頁標題` → `no_match`；改名為 `Cladue mod`（只是分頁標題的開頭）→ `no_match`；四次呼叫後前景視窗與選中分頁都沒變
- 收尾：每次實測後選回原本的 `✳ iPAS AI 中級戰情室` 並把前景還給原視窗，已確認兩者都還原；沒有關閉任何分頁或視窗，沒有碰 `~/.terminalpet/`，暫存資料已刪
- 架構檢查：`grep -n "write_text\|open(.*w" pet.py` 只出現 `CONFIG_FILE`；`wt_jump.py` 只有 `open(path, "rb")`，沒有任何寫入／刪除；`grep -n PySide6 set_state.py scripts/pet-state.sh wt_jump.py` 無結果
- 打包：venv 沒有 PyInstaller（未安裝）；改用標準庫 `modulefinder` 對 `pet.py` 做靜態 import 分析 → 找得到 `wt_jump`（`pet.py` 頂層 `import wt_jump`，與 `pet.py` 同資料夾），推論 PyInstaller 會自動收進，`build/pet.spec` 不需修改

**AI 驗不了、必須人工看的**：
- 實際在桌寵上按右鍵 → session 子選單 →「切換到終端機」，WT 被帶到最前面（不只工作列閃爍）——AI 是從背景程序以程式觸發選單動作（未經真的滑鼠點擊）；01 卡留下的「桌寵實點時的前景切換」也在這裡確認（不涉及金額／日期計算）
- AC-JUMP-04 的兩視窗情境：另一個 WT 視窗在最前面時，第一個（最小化）視窗還原並移到最前面、第二個視窗的分頁選取不變（本機只有 1 個 WT 視窗）
- AC-JUMP-06 真的用 `/rename` 改名後，選單切換能切到新名稱的分頁（AI 用假紀錄檔模擬）
- 系統匣（開啟桌面通知後）右鍵選單也出現「切換到終端機」且能切換（AC-NOTI-03 同步）
- 跳轉處理中拖曳、右鍵的手感（AI 只驗了事件迴圈不被卡住；本機跳轉只花 0.05～0.2 秒，人眼不易察覺）
- 非 Windows 系統實機（AI 只能以測試模擬 `sys.platform`）
- exe 打包後的實際行為（未實際打包）

**人工驗收結果（2026-10-09）**：
- 使用者 2026-10-09 於 Hub 匯出：人工必測「從桌寵右鍵實切」通過（含 01 卡留下的桌寵實點前景切換）；兩個 WT 視窗（AC-JUMP-04）、真的 /rename（AC-JUMP-06）兩項建議項略過

**可能因環境而異的行為**：
- UIA `Select` 會順帶把 WT 帶到前景，這是 WT 自身行為；WT 版本不同可能改變。本卡在 Select 後再呼叫 `SetForegroundWindow`，並以「0.5 秒內 `GetForegroundWindow()` 是該視窗」判定成功
- 前景切換受 Windows 前景鎖定規則影響；本機從背景程序觸發也成功（因 Select 的副作用），其他機器設定可能不同
- 分頁數多、WT 視窗多時，UIA 列分頁的耗時會增加（本機 1 視窗 3 分頁約 30～110 ms）

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

- 新模組 `wt_jump.py`（顯示端、只讀）：純函式 `read_tail`、`parse_title`、`read_session_title`、`is_same_tab`、`find_matches`；主流程 `jump_to_session(transcript) -> JumpResult(code, matches)`，任何錯誤都轉成結果代碼、不往外丟例外。結果代碼：`ok`、`no_title`、`no_window`、`no_match`、`ambiguous`（`matches` 是同名分頁數）、`failed`、`unsupported`
- 主流程分兩段：查找（`_jump_windows`：讀標題、EnumWindows 依 Z-order 列出 WT 視窗、UIA 列分頁、比對）與切換（`_switch`：IsIconic 才 SW_RESTORE → Select → SetForegroundWindow → 等前景）。本卡在 `no_title`／`no_window`／`no_match`／`ambiguous` 時**不動任何視窗**，只回傳代碼
- `pet.py`：`Session` 新增 `transcript` 欄位；新增 `JumpRunner(QObject)`——`start(transcript)` 開 daemon thread 執行跳轉，結果用 `finished` signal（`Signal(object)`）送回主執行緒；`PetWindow._on_jump_finished` 目前只把結果存到 `self._last_jump`
- 純 ctypes UI Automation（照 01 卡實作備註的 vtable 索引與 GUID），未安裝任何套件；worker 執行緒先 `CoInitializeEx(COINIT_MULTITHREADED)`，結束時 `CoUninitialize`；BSTR 讀完 `SysFreeString`，所有 COM 指標用完 Release
- 給後續卡的接點：04 卡可在 `_on_jump_finished` 依結果代碼顯示提示；在 `JumpRunner.start` 加世代編號／取消旗標與「處理中忽略」；在 `_switch` 的每個動作前檢查取消旗標；`no_title`／`no_match`／`ambiguous` 時「把最近使用的 WT 視窗帶到前面」可用 `wt_windows()` 的第一個（Z-order 最上層）。05、06 卡的點擊可直接呼叫 `PetWindow._jump_to(session.transcript)`
