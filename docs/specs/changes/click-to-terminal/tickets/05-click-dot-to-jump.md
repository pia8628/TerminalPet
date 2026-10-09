# 05-點圓點或清單列直接跳轉

**做完能 demo 什麼**：紅綠燈版左鍵點一下某個 session 的圓點（開啟「顯示專案名稱」時點整列也可以），就切到它的分頁；按住拖動超過門檻仍然是移動桌寵、不會跳轉；沒有 session 時點那顆灰點沒有任何反應。

**Blocked by**：03-右鍵「切換到終端機」

**狀態**：已完成

**檢查點**：否

## 規格依據

- US-JUMP-01
- AC-JUMP-01、AC-JUMP-02、AC-JUMP-07、AC-JUMP-08（點擊部分）、AC-JUMP-12
- 修改後的 AC-OPS-04（點一下不移動桌寵，點在圓點／清單列上才跳轉）

## 驗收條件

- [x] AC-JUMP-01（成功）：Given 同 03 卡的三分頁情境，外觀為紅綠燈版 → When 左鍵點一下 `abc123` 的圓點 → Then 切到第 2 個分頁；桌寵位置不變、不出現提示（「WT 移到最前面」本次實測時 WT 原本就在前景，未驗到從別的程式前面搶回前景，待人工）
- [x] AC-JUMP-02（成功）：Given 同上，已開啟「顯示專案名稱」 → When 點 `abc123` 那一列（圓點或文字） → Then 切到第 2 個分頁
- [x] AC-JUMP-07（邊界）：Given 左鍵按在某個圓點上 → When 拖動 30 px 後放開 → Then 桌寵移到新位置並記住位置，不切換分頁
- [x] AC-JUMP-08（邊界，點擊部分）：Given 非 Windows 系統 → When 點一下圓點 → Then 沒有任何反應、不出現提示（以假的 `supported()` 測試；本機是 Windows，實機待非 Windows 環境）
- [x] AC-JUMP-12（邊界）：Given 紅綠燈版、沒有 session、只顯示 1 顆灰點 → When 點一下灰點 → Then 沒有任何反應
- [x] AC-OPS-04（修改）：Given 桌寵在螢幕上 → When 點一下（移動未超過門檻）就放開 → Then 不更新記住的位置、桌寵不移動；點在圓點或清單列以外的位置沒有任何反應
- [x] 技術：拖曳門檻用 `QApplication.startDragDistance()`
- [x] 技術：既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**（全部 146 個測試與 ruff 全綠；本卡淨增 9 個。以 offscreen 平台＋`QApplication.sendEvent` 送真的 `QMouseEvent` 給桌寵，跳轉入口換成記錄器）：
- `tests/test_pet.py::test_AC_JUMP_01_click_dot_jumps_to_that_session` — 紅綠燈版點 `abc123` 圓點 → 用它的紀錄檔跳轉；桌寵位置不變、不存設定、不出提示
- `tests/test_pet.py::test_AC_JUMP_02_click_row_text_jumps_when_labels_shown` — 顯示專案名稱時點列的文字側、圓點側都跳該 session
- `tests/test_pet.py::test_AC_JUMP_07_drag_30px_from_dot_moves_and_saves_without_jump` — 按在圓點上拖 30 px：桌寵移 30 px、記住位置、不跳轉
- `tests/test_pet.py::test_AC_OPS_04_move_within_drag_threshold_is_a_click` — 移動剛好等於門檻（未超過）：不移動、不記位置、算點一下
- `tests/test_pet.py::test_AC_OPS_04_move_just_over_threshold_is_a_drag` — 門檻＋1：算拖曳、記位置、不跳轉
- `tests/test_pet.py::test_AC_OPS_04_click_outside_dots_does_nothing` — 點兩顆圓點中間的空隙、左上角邊緣：不跳、不動、不存
- `tests/test_pet.py::test_AC_JUMP_12_grey_dot_without_session_does_nothing` — 沒有 session 的灰點點了沒反應
- `tests/test_pet.py::test_AC_JUMP_08_click_on_non_windows_does_nothing` — 非 Windows 點圓點不跳轉、不出提示
- `tests/test_pet.py::test_animal_theme_click_does_not_move_or_save` — 動物版點一下不移動、不記位置（點小狼跳轉屬 06 卡，這裡不驗跳不跳）
- 反向確認（暫時改壞程式、確認變紅後還原，已用 `cmp` 確認檔案還原）：拿掉拖曳門檻 → `move_within_drag_threshold_is_a_click` 紅；拿掉灰點（None）檢查 → AC_JUMP_12 紅；拿掉非 Windows 檢查 → AC_JUMP_08 紅；拖曳放開也觸發點擊 → AC_JUMP_07、`just_over_threshold_is_a_drag` 紅；點擊不檢查命中區 → `click_outside_dots_does_nothing` 紅

**AI 實際操作驗過**（scratchpad 腳本 `live05.py`：session／設定資料夾全指向 scratchpad；Windows 真實平台建出紅綠燈版 `PetWindow`，用**系統層級滑鼠輸入**（`SetCursorPos`＋`mouse_event`，座標依螢幕縮放 125% 換算成實體像素）實際點擊／拖曳；本機 1 個 WT 視窗，分頁 `✳ Cladue mod 區塊修改`、`✳ iPAS AI 中級戰情室`、`◐ 先行執行的後果`、`✳ Claude Code`（原本選中、WT 原本就是前景）；假 session `abc123` 的標題設為 `Cladue mod 區塊修改`）：
- AC-JUMP-01：點 `abc123` 圓點 → 結果 `ok`、選中分頁變成 `✳ Cladue mod 區塊修改`；桌寵位置 (1266,696) 不變、設定檔沒有被寫、沒有提示
- AC-OPS-04：按在圓點上移動 2 px 放開（門檻 10）→ 仍算點一下並跳轉成功；桌寵不動、設定檔沒有被寫
- AC-OPS-04：點兩顆圓點中間的空隙 → 沒有跳轉（結果為空、選中分頁不變）、桌寵不動、設定檔沒有被寫
- AC-JUMP-07：按在 `abc123` 圓點上分三段拖 30 px → 桌寵 (1266,696) → (1296,696)、設定檔 `pos` 記為 [1296, 696]；沒有跳轉、選中分頁不變
- AC-JUMP-02：開「顯示專案名稱」後點 `abc123` 那一列的文字右端 → 跳轉 `ok`、選中 `✳ Cladue mod 區塊修改`；設定檔 `pos` 仍是 [1296, 696]（桌寵座標的變動是切換顯示模式時視窗改變大小、固定右下角造成，不是點擊）
- AC-JUMP-12：清空 session 後點唯一的灰點 → 沒有跳轉、選中分頁不變、設定檔 `pos` 未變
- 收尾：每項之後都選回原本的 `✳ Claude Code` 分頁；最後滑鼠游標放回原位，前景回到原本的 WT、WT 未最小化；沒有關閉任何分頁或視窗，沒有碰 `~/.terminalpet/`
- 架構檢查：`grep -n "write_text\|open(.*w" pet.py` 只出現 `CONFIG_FILE`

**AI 驗不了、必須人工看的**：
- AC-JUMP-01 從「別的程式在前景」的狀態點圓點，WT 真的被帶到最前面（本次實測時 WT 本來就在前景）（不涉及金額／日期計算）
- 實際手感：在圓點上輕點（手可能稍微抖動）是否穩定判定為點一下；按住拖動是否順手、拖曳開始時不會「跳一下」（門檻 10 px，見下方環境差異）
- AC-JUMP-08 非 Windows 實機（本機是 Windows，只用假的 `supported()` 測）
- 點擊後與滑鼠停留提示（AC-VIEW-10）、waiting 閃燈（AC-VIEW-09）同時出現時的觀感；右鍵選單照常（程式沒動這兩塊，既有測試全綠）

**可能因環境而異的行為**：
- 拖曳門檻取 `QApplication.startDragDistance()`，本機回傳 **10（邏輯像素，125% 縮放下約 12.5 實體像素）**，不是 delta 名詞定義寫的「Windows 預設約 4 px」——Qt 沒有沿用 Windows 的 `SM_CXDRAG`。依卡上的技術條文照用 Qt 值；若使用者覺得輕微拖動被當成點擊，可回頭討論
- 移動距離用 `manhattanLength()`（|dx|+|dy|，Qt 慣例），斜向移動會比直線距離早一點達到門檻
- 前景切換受 Windows 前景鎖定規則影響（見 04 卡）；從桌寵實點時桌寵擁有前景權，通常可行

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

- `pet.PetWindow` 拖曳改為「按下記錄全域座標 → 移動超過 `QApplication.startDragDistance()`（`manhattanLength`，嚴格大於）才開始移動並標記 `_dragged` → 放開時拖過就存位置，否則呼叫 `_on_click(放開位置)`」。新增 `_pressed` 旗標，沒有在桌寵上按下的放開事件不處理
- `PetWindow._on_click(pos)`：目前只處理紅綠燈版（`theme == "light"`）且 `wt_jump.supported()`；命中 `self._hits` 中 session 不為 None 的區塊才呼叫 `self._jump_to(s.transcript)`；命中灰點（None）或沒命中都直接返回。非 Windows 在點擊端就擋掉，不會啟動背景執行緒
- 給 06 卡：在 `_on_click` 開頭的 `theme != "light"` 分支改成處理動物版——點在 `self._wolf_rect` 內就挑目標 session 呼叫 `_jump_to`。注意動物版 `self._hits` 也有小狼下方的 session 小圓點（多個 session 或開顯示專案名稱時），本卡沒有讓它們可點；要不要可點依 delta AC-OPS-04 修改條文（「session 圓點、清單列或小狼」）由 06 卡決定。`test_animal_theme_click_does_not_move_or_save` 只守不移動、不存位置，不擋 06 卡加跳轉
