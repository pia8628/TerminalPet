# 02-寫入端記錄對話紀錄檔路徑

**做完能 demo 什麼**：在 Claude Code 裡做任何會觸發 hook 的事之後，`~/.terminalpet/sessions/<sid>.json` 多了 `transcript` 欄位，值是對話紀錄檔的路徑（正斜線）；用 `python set_state.py waiting` 寫入的假 session，這個欄位是空字串。

**Blocked by**：無——可直接開工（可與 01 平行）

**狀態**：已完成

**檢查點**：否

## 規格依據

- US-HOOK-04
- AC-HOOK-15、AC-HOOK-16

## 驗收條件

- [x] AC-HOOK-15（成功）：Given hook 資料帶有 `transcript_path` = `C:\Users\me\.claude\projects\D--Projects-TerminalPet\abc123.jsonl` → When 觸發任一會寫入狀態的事件 → Then 狀態檔的 `transcript` 為 `C:/Users/me/.claude/projects/D--Projects-TerminalPet/abc123.jsonl`，其他欄位與既有行為（AC-HOOK-09～14）相同
- [x] AC-HOOK-16（邊界）：Given hook 資料沒有 `transcript_path` → When 觸發會寫入狀態的事件 → Then `transcript` 為空字串，狀態照常寫入
- [x] 技術：`set_state.py` 寫入的狀態檔也有 `transcript`（空字串）
- [x] 技術：`pet-state.sh` 仍只用 bash 內建指令、出錯時靜默結束；`tests/test_pet_state.py` 延伸測試，既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**：
- tests/test_pet_state.py::test_T15_AC_HOOK_15_transcript_path_normalized（idle／thinking／working／waiting／done 五種狀態參數化）— AC-HOOK-15：`transcript` 轉正斜線，且 state、sid、project、cwd 維持 AC-HOOK-09 既有行為
- tests/test_pet_state.py::test_T16_AC_HOOK_15_transcript_with_existing_file_keeps_since — AC-HOOK-15：已有狀態檔時照樣寫入 `transcript`，since／start 沿用規則（AC-HOOK-13）不受影響
- tests/test_pet_state.py::test_T17_AC_HOOK_16_no_transcript_path_writes_empty（有 session_id 但無 transcript_path、stdin 完全沒資料兩種）— AC-HOOK-16：`transcript` 為空字串、狀態照常寫入
- tests/test_pet_state.py::test_T18_transcript_parsing_uses_only_bash_builtins — 技術條件：新欄位的解析行不含 jq／python／sed／grep／awk／cat／`$(`／反引號等外部呼叫
- tests/test_set_state.py::test_T11_AC_HOOK_16_set_state_writes_empty_transcript — 技術條件：`set_state.py` 寫入 `transcript` 空字串
- 既有 T01～T14（含 AC-HOOK-09～14、結束碼 0 檢查）全數仍綠；全套 62 passed、0 skipped，ruff 全綠
- 反向確認：①拿掉反斜線轉換那一行 → T15×5、T16 共 6 個紅；②拿掉取 `transcript_path` 那一行 → T15、T16 紅；③把預設值改成 "x" → T17×2 紅；④`set_state.py` 改寫 None → test_set_state T11 紅。均已還原、全綠

**AI 實際操作驗過**：
- 以 HOME 指向 scratchpad 暫存資料夾，用 Git Bash 餵 `{"session_id":"abc123","cwd":"D:\Projects\TerminalPet","transcript_path":"C:\Users\me\.claude\projects\D--Projects-TerminalPet\abc123.jsonl"}` 執行 `pet-state.sh working` → 結束碼 0，狀態檔 `"transcript":"C:/Users/me/.claude/projects/D--Projects-TerminalPet/abc123.jsonl"`，project=TerminalPet、cwd=D:/Projects/TerminalPet
- 餵只有 session_id、cwd 的資料執行 `done` → `"transcript":""`，其他欄位正常
- stdin 不給資料執行 `idle` → 寫入 default.json，`"transcript":""`
- 餵截斷的壞 JSON（`transcript_path":"x` 沒收尾）→ 結束碼 0、`"transcript":""`，狀態照常寫入（靜默不出錯）
- `set_state.py waiting`（SESSIONS_DIR 指向暫存資料夾）→ 檔案含 `"transcript": ""`；`pet.load_sessions()` 讀上述五個檔皆正常列出（多一個欄位不影響桌寵，故未動 pet.py）

**AI 驗不了、必須人工看的**：
- 真實 Claude Code session 觸發 hook 後，`~/.terminalpet/sessions/<sid>.json` 確實出現 `transcript` 且路徑指向真實存在的 .jsonl（依賴 Claude Code 實際送出的 `transcript_path` 欄位；需重裝／更新 plugin 或 install.py 安裝的 hook 才會用到新腳本）。不涉及金額／日期計算

**可能因環境而異的行為**：
- macOS 內建 bash 3.2：新解析只用 `[[ =~ ]]` 與 `${var//}`，與 cwd 相同手法，應無差異，但本機未在 macOS 實測
- 路徑若含 `"`（JSON 中為 `\"`），擷取會在該處截斷——與既有 cwd 的限制相同，Windows 路徑不允許 `"`，實務上不會發生

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

- 專案內只有一份 `scripts/pet-state.sh`；plugin（`hooks/hooks.json`）與 `install.py` 都直接引用它，不需同步第二份。
- `pet.py` 讀檔用 `data.get(...)`，多出的 `transcript` 欄位不影響現有顯示，本卡未改 pet.py（讀取 `transcript` 屬後續卡）。
- `tests/cases/狀態寫入.md`、`手動測試工具.md` 是使用者 review 過的案例表，本卡未擅自追加 T15～T18／T11 的列，留待驗收時補登。

