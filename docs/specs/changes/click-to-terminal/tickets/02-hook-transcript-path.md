# 02-寫入端記錄對話紀錄檔路徑

**做完能 demo 什麼**：在 Claude Code 裡做任何會觸發 hook 的事之後，`~/.terminalpet/sessions/<sid>.json` 多了 `transcript` 欄位，值是對話紀錄檔的路徑（正斜線）；用 `python set_state.py waiting` 寫入的假 session，這個欄位是空字串。

**Blocked by**：無——可直接開工（可與 01 平行）

**狀態**：待做

**檢查點**：否

## 規格依據

- US-HOOK-04
- AC-HOOK-15、AC-HOOK-16

## 驗收條件

- [ ] AC-HOOK-15（成功）：Given hook 資料帶有 `transcript_path` = `C:\Users\me\.claude\projects\D--Projects-TerminalPet\abc123.jsonl` → When 觸發任一會寫入狀態的事件 → Then 狀態檔的 `transcript` 為 `C:/Users/me/.claude/projects/D--Projects-TerminalPet/abc123.jsonl`，其他欄位與既有行為（AC-HOOK-09～14）相同
- [ ] AC-HOOK-16（邊界）：Given hook 資料沒有 `transcript_path` → When 觸發會寫入狀態的事件 → Then `transcript` 為空字串，狀態照常寫入
- [ ] 技術：`set_state.py` 寫入的狀態檔也有 `transcript`（空字串）
- [ ] 技術：`pet-state.sh` 仍只用 bash 內建指令、出錯時靜默結束；`tests/test_pet_state.py` 延伸測試，既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**：
- 

**AI 實際操作驗過**：
- 

**AI 驗不了、必須人工看的**：
- 

**可能因環境而異的行為**：
- 

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

