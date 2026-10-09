# 06-點小狼跳到最需要注意的 session

**做完能 demo 什麼**：動物版左鍵點一下小狼，就切到「最需要注意」的那個 session 的分頁（依 waiting → done → working → thinking 的順序，同一種狀態挑最早出現的）；所有 session 都是 idle 或沒有 session 時，點了沒有任何反應。

**Blocked by**：05-點圓點或清單列直接跳轉

**狀態**：已完成

**檢查點**：否

## 規格依據

- US-JUMP-02
- AC-JUMP-09、AC-JUMP-10、AC-JUMP-11

## 驗收條件

- [x] AC-JUMP-09（成功）：Given 動物版，A（working，首次出現 100）、B（waiting，200）、C（waiting，300），都有同名分頁 → When 左鍵點一下小狼 → Then 切到 B 的分頁
- [x] AC-JUMP-10（成功）：Given 動物版，A（thinking，100）、B（done，200） → When 點一下小狼 → Then 切到 B 的分頁
- [x] AC-JUMP-11（邊界）：Given 動物版，所有 session 都顯示為 idle（含逾時轉 idle 者）或沒有 session → When 點一下小狼 → Then 沒有任何反應：不切換視窗、不出現提示
- [x] 技術：挑選目標 session 的規則寫成純函式，用假資料寫進 `tests/test_pet.py`
- [x] 技術：既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**：
- `tests/test_pet.py::test_AC_JUMP_09_wolf_target_is_earliest_of_most_urgent_state` — 純函式：A working 100、B waiting 200、C waiting 300 → 挑 B
- `tests/test_pet.py::test_AC_JUMP_10_wolf_target_follows_waiting_done_working_thinking_order` — 純函式：thinking＋done → done；thinking＋working → working；idle＋thinking → thinking；done＋waiting → waiting
- `tests/test_pet.py::test_AC_JUMP_09_wolf_target_matches_wolf_display_state` — 挑到的狀態一定等於小狼顯示的狀態（`aggregate_state`）
- `tests/test_pet.py::test_AC_JUMP_11_wolf_target_none_when_all_idle_or_empty` — 純函式：沒有 session、全部 idle → None
- `tests/test_pet.py::test_AC_JUMP_11_wolf_target_none_when_busy_sessions_timed_out` — 從 session 檔讀入：working／thinking 超過 600 秒、done 超過 1800 秒都轉 idle → None
- `tests/test_pet.py::test_AC_JUMP_09_click_wolf_jumps_to_earliest_waiting` — 動物版視窗（Qt offscreen）左鍵點小狼 → 只觸發 B 的跳轉，桌寵不移動、不存位置
- `tests/test_pet.py::test_AC_JUMP_10_click_wolf_jumps_to_done_over_thinking` — 點小狼 → 觸發 B（done）的跳轉
- `tests/test_pet.py::test_AC_JUMP_11_click_wolf_all_idle_or_timed_out_does_nothing` — 一個 idle＋兩個逾時轉 idle，點小狼 → 不呼叫跳轉、不出提示
- `tests/test_pet.py::test_AC_JUMP_11_click_wolf_without_sessions_does_nothing` — 沒有 session，點小狼 → 不呼叫跳轉、不出提示
- `tests/test_pet.py::test_animal_click_outside_wolf_does_nothing` — 動物版小狼下方的 session 小圓點點了沒反應（維持現狀，見實作備註）
- `tests/test_pet.py::test_AC_JUMP_08_click_wolf_on_non_windows_does_nothing` — 非 Windows 點小狼不動作
- 反向確認（暫改程式後跑、再還原）：同狀態改挑最晚 → AC_JUMP_09 兩支變紅；拿掉 idle 保護 → AC_JUMP_11 四支變紅；拿掉小狼範圍判定 → outside_wolf 變紅；拿掉非 Windows 擋 → AC_JUMP_08_click_wolf 變紅

**AI 實際操作驗過**：
- 用暫存腳本以真的 Windows 平台（非 offscreen）開動物版桌寵，session 資料夾與 CONFIG_FILE 都指到 scratchpad，用系統滑鼠（`SetCursorPos`＋`mouse_event`）左鍵點小狼中心：
  - AC-JUMP-09 資料（A working 100、B waiting 200、C waiting 300）→ 觸發跳轉的紀錄檔只有 `C:/t/B.jsonl`，桌寵位置不變、沒存設定、沒提示（跳轉函式換成記錄器，未實際切分頁）
  - AC-JUMP-10 資料（A thinking 100、B done 200）→ 只觸發 `C:/t/B.jsonl`
  - AC-JUMP-11：A idle、B working 但 601 秒沒更新、C done 但 1801 秒沒更新 → 讀進來三者都是 idle；點小狼後等 2 秒，沒觸發跳轉、`_last_jump` 仍是 None、沒有提示
  - AC-JUMP-11：沒有 session → 同上，沒有任何反應
  - 兩個 session 時點小狼下方的小圓點 → 沒觸發跳轉
  - 走真實跳轉鏈（不換記錄器）：唯一 session 是 waiting、紀錄檔路徑不存在 → 背景跳轉回 `no_title`，桌寵旁出現提示「找不到這個 session 的分頁」（依 04 卡設計，此情況會把最近使用的 WT 叫到前面）；確認點小狼確實接上 `_jump_to` → JumpRunner → wt_jump 整條鏈
  - 結束後滑鼠游標移回原位，前景視窗與開始前相同（比對 HWND 為 True），暫存 session 資料夾已刪
- 全部測試 157 passed、ruff 全綠

**AI 驗不了、必須人工看的**：
- 真的有多個同名 WT 分頁時，點小狼實際切到「最需要注意」那個分頁（AC-JUMP-09、10 的 Then「切到 B 的分頁」）——本次自驗只確認挑對 session 並把它的紀錄檔交給跳轉，實際選分頁由 03～05 卡已驗的同一條跳轉鏈負責
- AC-JUMP-11 的「不切換視窗」在真實環境下的手感（點下去畫面完全沒動靜）

**可能因環境而異的行為**：
- 逾時轉 idle 依本機時鐘與 session 檔 `ts` 比較；點擊判定的「小狼範圍」是 120×120 方框（含圖片透明邊），點在小狼圖案旁的透明角落也算點到小狼

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

- 新增純函式 `pet.wolf_jump_target(sessions)`：直接重用 `aggregate_state`（小狼顯示用的同一個彙整）取得最需要注意的狀態，idle 回 None；同狀態取 `start` 最小者（同 `start` 再比 sid）。`Session.state` 已是 `effective_state` 套過逾時規則的有效狀態，所以和小狼顯示一致，沒有另寫一套優先序。已確認 `STATE_PRIORITY`（waiting 4 > done 3 > working 2 > thinking 1 > idle 0）與本卡規則一致
- `PetWindow._on_click`：開頭改為只擋非 Windows；動物版點在 `self._wolf_rect` 內才挑目標並呼叫 `_jump_to`，其他位置（含小狼下方的 session 小圓點／清單列）一律 return。紅綠燈版邏輯不變
- 規格模糊處（未處理，調度員已記下要問使用者）：delta 修改後的 AC-OPS-04 寫「點在 session 圓點、清單列或小狼上時……跳轉」，動物版的小圓點／清單列要不要也能點，卡上沒寫；本卡維持點了沒反應，並以 `test_animal_click_outside_wolf_does_nothing` 守住現狀，若之後決定要可點，改這支測試即可
