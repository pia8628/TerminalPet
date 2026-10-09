# 長線開發紀錄：click-to-terminal

**狀態**：進行中（進行中／暫停／已跑完）

**分支**：`feature/click-to-terminal`

**開始**：2026-10-09

> 由 `/dev-run-card` 維護。對話中斷後開新對話說 `/dev-run-card` 或「繼續長線」，會照這份接著跑。

## 佇列

| 順序 | 卡 | 檢查點 | 狀態 | 備註 |
|------|----|--------|------|------|
| 1 | 01-可行性實驗 | 是 | 已驗收 | 2026-10-09 驗收；delta 已加入 `◑`、terminalTitleFromRename=false 列入 Out of Scope |
| 2 | 02-寫入端記錄對話紀錄檔路徑 | 否 | 已完成（待人工驗收） | 62 測試全綠 |
| 3 | 03-右鍵「切換到終端機」 | 是 | 已完成（待人工驗收） | 106 測試全綠；檢查點：使用者 2026-10-09 表示沒空、同意先往下跑，人工驗收延到全部跑完一起做 |
| 4 | 04-跳不過去時的提示與保護 | 否 | 已完成（待人工驗收） | 137 測試全綠 |
| 5 | 05-點圓點或清單列直接跳轉 | 否 | 已完成（待人工驗收） | 146 測試全綠 |
| 6 | 06-點小狼跳到最需要注意的 session | 否 | 已完成（待人工驗收） | 157 測試全綠 |

狀態只用這幾種：待做／施工中／已完成（待人工驗收）／已驗收／熔斷／跳過（被 NN 擋住）／結果不明（中斷，等人判斷要不要重派）

## 熔斷紀錄

無

## 發現

（跑的過程中看到、但不屬於任何一張卡的事：該進 `.gitignore` 的產物、卡外的 bug、規格模糊處。收尾時一起回報。）

- 01 卡：狀態前綴實測多出 `◑`（U+25D1），delta「狀態前綴」與 `STATUS_PREFIXES` 待使用者決定是否修訂（檢查點）
- 01 卡：使用者設定 `terminalTitleFromRename: false` 時分頁維持 AI 標題，custom-title 優先會比對失敗——待使用者決定處理或列入 Out of Scope
- 01 卡（給 03、04 卡）：UIA `Select` 會順帶把 WT 帶到前景；建議順序「IsIconic 才 SW_RESTORE → Select → SetForegroundWindow」，以 `GetForegroundWindow()==hwnd` 判定 AC-JUMP-19；改名為空字串時要退回 ai-title
- 02 卡：新測試 T15～T18（test_pet_state）、T11（test_set_state）尚未補進 `tests/cases/狀態寫入.md`、`tests/cases/手動測試工具.md` 案例表（使用者 review 過的表，子代理未擅改）——待使用者決定是否補
- 02 卡：真實 session 要更新 plugin／重跑 install.py 後，hook 才會寫入 `transcript`
- 03 卡：本機 hook 是 install.py 安裝的 `~/.claude/scripts/pet-state.sh`（舊版），驗收前需使用者重跑 `python install.py`
- 03 卡：`CLAUDE.md` 架構表「位置」欄仍只寫 `pet.py`，`wt_jump.py` 只註明在職責欄——是否補進位置欄待使用者決定
- 03 卡（給 04 卡）：`wt_jump.jump_to_session()` 回傳 `JumpResult(code, matches)`，code 七種（ok/no_title/no_window/no_match/ambiguous/failed/unsupported）；切換段 `_switch` 每步前可插取消檢查；`JumpRunner` + `_on_jump_finished` 目前只存結果
- 04 卡：`wt_windows()` 沒有過濾隱藏的 WT 視窗，有隱藏視窗時「最近使用的 WT」可能挑到看不見的那個（已記在卡上，未處理）
- 04 卡：scratchpad 留有子代理的暫存檔（`live04*`、`*.bak`、`h02/`），在 repo 外，不影響專案
- 05 卡：拖曳門檻用 `QApplication.startDragDistance()`，本機為 10 px，與 delta 名詞定義「Windows 預設約 4 px」描述不同——驗收時請使用者試手感
- 05 卡：動物版小狼下方的 session 小圓點／清單列能否點擊跳轉，delta 修改後的 AC-OPS-04 寫「session 圓點、清單列或小狼」，但 05、06 卡都只寫紅綠燈版圓點與小狼——規格模糊，06 卡不做，待使用者決定
- 06 卡：小狼點擊範圍是 120×120 方框，含圖片四周透明角落
