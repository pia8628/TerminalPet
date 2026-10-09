/* docs/verify/data.js —— TerminalPet 驗收資料
 *
 * 由 Claude 在 /dev-verify-card、/dev-run-card、/dev-verify-spec 追加／更新，使用者不需要手改。
 * item.id 必須穩定：{changeId}/{ticketId}/{規格條文編號或短語意鍵}。
 * allTicketsLoaded 只有 /dev-verify-spec 能改成 true。
 */
window.VERIFY_DATA = {
  project: "TerminalPet",
  generatedAt: "2026-10-09",

  environments: [
    { id: "win11-wt", label: "Windows 11 + Windows Terminal" }
  ],

  changes: [
    {
      id: "click-to-terminal",
      name: "點擊跳到終端機",
      status: "verifying",
      closedAt: null,
      closedNote: "",
      specRef: "docs/specs/changes/click-to-terminal/delta.md",
      allTicketsLoaded: false,

      tickets: [
        {
          id: "01-feasibility-spike",
          title: "01 可行性實驗：列出 WT 分頁並依標題切換（檢查點）",
          verified: { at: "2026-10-09T19:25:04+08:00", note: "使用者在對話中回報驗完 OK；依建議於 delta 加入 `◑`、terminalTitleFromRename=false 列入 Out of Scope" },
          items: [
            {
              id: "click-to-terminal/01-feasibility-spike/rename-tab-title",
              text: "在任一個 Claude Code 分頁輸入：\n\n```\n/rename 跳轉測試\n```\n\n預期：\n- 這個分頁的標題變成 `✳ 跳轉測試`（或執行中時是 `◐`／`◑` 開頭）\n- 想改回原名可以再 `/rename` 一次\n\n> 這項決定 AC-JUMP-06（改名後要用新名稱比對）能不能照原規格做。AI 沒辦法執行 slash command，只能從 Claude Code 程式碼推論「會變」。",
              spec: { ref: "delta.md AC-JUMP-06、Implementation Decisions「改名紀錄格式」", quote: "分頁標題在改名後是否顯示新名稱，列入第一張卡的可行性實驗；若不顯示，AC-JUMP-06 改為「以自動標題比對」並回頭修訂本規格。" },
              risk: "medium",
              riskReason: "結論只來自程式碼推論；若實際不顯示新名稱，03 卡的標題規則要改",
              coverage: {
                auto:  { covered: false, ref: "" },
                agent: { covered: false, how: "" }
              },
              manualOnly: false,
              manualOnlyReason: "AI 不能執行 `/rename`；錯了在 03 卡驗收時也看得出來，不傷資料",
              manualSuggested: true,
              crossEnv: false,
              result: { status: "pass", note: "使用者在對話中回報通過", at: "2026-10-09T19:25:04+08:00" }
            },
            {
              id: "click-to-terminal/01-feasibility-spike/waiting-prefix",
              text: "讓某個 Claude Code session 停在**等你批准**的狀態（例如它要執行一個需要你按允許的指令），先**不要**按，看那個分頁的標題。\n\n預期：\n- 分頁標題開頭是 `✳ `（不是其他符號）\n\n> 如果看到 `✳`、`◐`、`◑` 以外的符號，請把那個符號告訴我，規格的狀態前綴清單要再補。",
              spec: { ref: "delta.md 名詞定義「狀態前綴」", quote: "狀態符號只認明確清單：`✳`（U+2733，閒置）、`◐`（U+25D0，執行中）" },
              risk: "medium",
              riskReason: "AI 無法觸發等批准狀態，只能依程式碼推論是 `✳`；清單漏符號會讓紅燈 session 跳不過去",
              coverage: {
                auto:  { covered: false, ref: "" },
                agent: { covered: false, how: "" }
              },
              manualOnly: false,
              manualOnlyReason: "AI 觸發不了等批准；錯了只是跳不過去，容易發現",
              manualSuggested: true,
              crossEnv: false,
              result: { status: "pass", note: "使用者在對話中回報通過", at: "2026-10-09T19:25:04+08:00" }
            },
            {
              id: "click-to-terminal/01-feasibility-spike/uia-list-match-select",
              text: "用 UI Automation 列出所有 WT 分頁、從對話紀錄檔取標題比對，並把最小化的 WT 還原、選中分頁、帶到前景。\n\n預期：\n- 列得出分頁名稱與目前選中哪一個\n- 標題去掉狀態前綴後與分頁完全相同\n- 最小化的視窗能還原並選中目標分頁",
              spec: { ref: "01 卡驗收條件 1、2、5（前半）", quote: "" },
              risk: "low",
              riskReason: "技術可行性已實測，後續卡會再驗一次真實流程",
              coverage: {
                auto:  { covered: false, ref: "" },
                agent: { covered: true, how: "子代理用 ctypes 直呼 UIAutomationCore：本機 WT 列出 3 個分頁（40～110 ms，worker thread 也可）；19 個 jsonl 只讀檔尾 1 MB 取到 14 個標題，2 個對到唯一同名分頁；`.env`／`env` 等反例都判為不同名；SW_MINIMIZE → UIA Select → SW_RESTORE + SetForegroundWindow 成功還原、成為前景、選中目標分頁" }
              },
              manualOnly: false,
              manualOnlyReason: "",
              manualSuggested: false,
              crossEnv: false,
              result: { status: "pass", note: "使用者在對話中回報通過", at: "2026-10-09T19:25:04+08:00" }
            },
            {
              id: "click-to-terminal/01-feasibility-spike/status-prefix-sampling",
              text: "取樣不同狀態下的分頁標題前綴。\n\n預期：只出現規格清單內的符號。\n\n**實測結果：多出 `◑`（U+25D1）**——執行中的 session 在分頁被聚焦時，前綴會在 `◐`／`◑` 間每 960 ms 交替。要不要把 `◑` 加進規格，請在對話裡決定。",
              spec: { ref: "delta.md 名詞定義「狀態前綴」", quote: "發現清單外的狀態符號時，回頭修訂本規格的狀態前綴清單後才實作。" },
              risk: "high",
              riskReason: "不補 `◑` 的話，你正在看的那個執行中分頁約有一半機率跳不過去",
              coverage: {
                auto:  { covered: false, ref: "" },
                agent: { covered: true, how: "背景 8 秒取樣 40 次只見 `✳`、`◐`；WT 在前景並選中執行中分頁時 3 秒取樣見 `◐`、`◑`、`✳`；Claude Code 2.1.295 程式碼 `S6=[\"◐\",\"◑\"]`、`b6=\"✳\"` 佐證" }
              },
              manualOnly: false,
              manualOnlyReason: "",
              manualSuggested: false,
              crossEnv: false,
              result: { status: "pass", note: "使用者在對話中回報通過", at: "2026-10-09T19:25:04+08:00" }
            }
          ]
        },
        {
          "id": "02-hook-transcript-path",
          "title": "02 寫入端記錄對話紀錄檔路徑",
          "items": [
            {
              "id": "click-to-terminal/02-hook-transcript-path/AC-HOOK-15",
              "text": "hook 收到帶 Windows 路徑的 `transcript_path` 時，狀態檔多一個 `transcript` 欄位，反斜線轉成正斜線。\n\n預期：\n- `C:\\Users\\me\\.claude\\projects\\D--Projects-TerminalPet\\abc123.jsonl` 寫成 `C:/Users/me/.claude/projects/D--Projects-TerminalPet/abc123.jsonl`\n- 其他欄位（state、since、start、project、cwd）行為不變",
              "spec": {
                "ref": "delta.md AC-HOOK-15",
                "quote": "狀態檔多一個紀錄檔路徑欄位……（反斜線轉正斜線）；其他欄位與既有行為（AC-HOOK-09～14）相同"
              },
              "risk": "low",
              "riskReason": "純字串轉換，五種狀態都有測試並做過反向確認",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet_state.py::test_T15_AC_HOOK_15_transcript_path_normalized、test_T16_AC_HOOK_15_transcript_with_existing_file_keeps_since"
                },
                "agent": {
                  "covered": true,
                  "how": "HOME 指向暫存資料夾，用 Git Bash 餵 JSON 執行 `pet-state.sh working` → 結束碼 0，`transcript` 為正斜線路徑，project／cwd 正確"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false
            },
            {
              "id": "click-to-terminal/02-hook-transcript-path/AC-HOOK-16",
              "text": "hook 資料沒有 `transcript_path`、stdin 沒資料、或 JSON 壞掉，以及 `set_state.py` 寫的假 session。\n\n預期：\n- `transcript` 為空字串\n- 狀態照常寫入、腳本不報錯（結束碼 0）",
              "spec": {
                "ref": "delta.md AC-HOOK-16",
                "quote": "紀錄檔路徑欄位為空字串，狀態照常寫入"
              },
              "risk": "low",
              "riskReason": "有測試涵蓋，壞 JSON 也實際跑過",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet_state.py::test_T17_AC_HOOK_16_no_transcript_path_writes_empty、tests/test_set_state.py::test_T11_AC_HOOK_16_set_state_writes_empty_transcript"
                },
                "agent": {
                  "covered": true,
                  "how": "實際執行：無 transcript_path → 空字串；stdin 空 → default.json 空字串；截斷的壞 JSON → 結束碼 0；`set_state.py waiting` 含 `\"transcript\": \"\"`，`pet.load_sessions()` 正常讀取"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false
            },
            {
              "id": "click-to-terminal/02-hook-transcript-path/real-session",
              "text": "更新 plugin（或重跑 `install.py`）讓 hook 用到新版腳本後，在任一個 Claude Code session 隨便問一句話，再打開：\n\n```\n%USERPROFILE%\\.terminalpet\\sessions\\<那個 session 的 id>.json\n```\n\n預期：\n- 檔案裡有 `\"transcript\":\"C:/Users/.../xxx.jsonl\"`\n- 照那個路徑去找，檔案真的存在",
              "spec": {
                "ref": "02 卡「做完能 demo 什麼」",
                "quote": ""
              },
              "risk": "medium",
              "riskReason": "依賴 Claude Code 實際送出的欄位；沒有這欄，後面的跳轉功能全部找不到標題",
              "coverage": {
                "auto": {
                  "covered": false,
                  "ref": ""
                },
                "agent": {
                  "covered": false,
                  "how": ""
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "要真的 session 觸發安裝後的 hook；錯了在 03 卡驗收時會直接看到跳不過去，容易發現",
              "manualSuggested": true,
              "crossEnv": false
            }
          ]
        }
      ]
    }
  ]
};
