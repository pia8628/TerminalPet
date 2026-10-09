# 07-動物版點小圓點或清單列直接跳轉

**做完能 demo 什麼**：動物版左鍵點一下小狼下方某個 session 的小圓點（開啟「顯示專案名稱」時點整列也可以），就切到它的分頁；點小狼仍是跳到最需要注意的 session。

**Blocked by**：05-點圓點或清單列直接跳轉、06-點小狼跳到最需要注意的 session

**狀態**：已驗收（2026-10-09）

**檢查點**：否

> 來源：2026-10-09 驗收後使用者決定「動物版的小圓點也要可以點」。delta 修改後的 AC-OPS-04 已寫「點的位置在 session 圓點、清單列或小狼上時……跳轉」，原本拆卡時漏列動物版的圓點／清單列，本卡補上，規格不變。

## 規格依據

- US-JUMP-01
- 修改後的 AC-OPS-04（點在 session 圓點、清單列或小狼上才跳轉）
- AC-JUMP-01、AC-JUMP-02、AC-JUMP-07、AC-JUMP-08（點擊部分）的動物版對應情境

## 驗收條件

- [x] AC-OPS-04（動物版）：Given 動物版、有 session A、B → When 左鍵點一下 B 的小圓點 → Then 切到 B 的分頁（不是小狼挑的目標）；桌寵不移動、不記位置
- [x] AC-JUMP-02（動物版）：Given 動物版、已開啟「顯示專案名稱」 → When 點 B 那一列的文字 → Then 切到 B 的分頁
- [x] AC-JUMP-07（動物版）：Given 左鍵按在小圓點上 → When 拖動超過門檻後放開 → Then 桌寵移動並記住位置，不跳轉
- [x] AC-JUMP-08（動物版）：Given 非 Windows → When 點小圓點 → Then 沒有任何反應
- [x] 技術：點小狼的行為（AC-JUMP-09～11）不變；既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**：
- tests/test_pet.py::test_AC_OPS_04_animal_click_dot_jumps_to_that_session — 點 B 的小圓點切到 B（小狼會挑 A），桌寵不動、不記位置
- tests/test_pet.py::test_AC_JUMP_02_animal_click_row_text_jumps_when_labels_shown — 開專案名稱後點列的文字端切到 B
- tests/test_pet.py::test_AC_JUMP_07_animal_drag_from_dot_moves_without_jump — 從小圓點拖 30 px：移動並記位置、不跳轉
- tests/test_pet.py::test_AC_JUMP_08_animal_click_dot_on_non_windows_does_nothing — 非 Windows 點小圓點無反應
- tests/test_pet.py::test_animal_click_outside_wolf_and_dots_does_nothing — 點小狼與小圓點以外的角落無反應（取代原 test_animal_click_outside_wolf_does_nothing）
- 點小狼的 AC-JUMP-09～11 既有測試全綠；全套 161 passed、ruff 全綠
- 反向確認：暫時讓動物版在小狼以外直接 return → 前兩支測試紅；還原後全綠

**AI 實際操作驗過**：
- 無真實平台實點（點擊判定與跳轉流程和 05 卡紅綠燈版共用同一段程式，05 卡已用系統滑鼠實測）

**AI 驗不了、必須人工看的**：
- 動物版實際點小狼下方的小圓點／清單列，WT 切到那個 session 的分頁（不涉及金額／日期計算）

**人工驗收結果（2026-10-09）**：
- 使用者在對話中回報通過（動物版實點小圓點／清單列）

**可能因環境而異的行為**：
- 動物版只有 1 個 session 且未開專案名稱時不畫小圓點（既有行為），此時只有小狼可點

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

- `_on_click`：動物版點在小狼內走 `wolf_jump_target`；其他位置與紅綠燈版共用 `_hits` 判定。改動只在 `pet.py` 的 `_on_click` 與模組開頭說明。
