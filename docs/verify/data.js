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
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者未填（AI 已驗過・可略過）",
                "at": "2026-10-09T22:57:41+08:00"
              }
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
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:54:14.124Z"
              }
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
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:54:07.199Z"
              }
            }
          ],
          "verified": {
            "at": "2026-10-09T22:57:41+08:00",
            "note": "使用者 2026-10-09 匯出結果：AI 驗過的項目略過／未填；真實 session 項略過（03 卡右鍵實切通過，間接證明 transcript 已寫入）"
          }
        },
        {
          "id": "03-menu-switch-to-terminal",
          "title": "03 右鍵「切換到終端機」（檢查點）",
          "items": [
            {
              "id": "click-to-terminal/03-menu-switch-to-terminal/AC-JUMP-03",
              "text": "**前置**：先在終端機跑一次 `python install.py`（讓 hook 用到 02 卡的新版腳本），然後重開桌寵；每個要測的 Claude Code 分頁都先隨便問一句話，讓狀態檔記下紀錄檔路徑。\n\n在 WT 裡開 2～3 個 Claude Code 分頁，先選中第 1 個，再切到別的程式（例如瀏覽器）。對桌寵按右鍵 → 選第 2 個 session 的子選單。\n\n預期：\n- 子選單依序是「切換到終端機」→「開啟資料夾」→「從清單移除」\n- 按「切換到終端機」後，WT **跳到最前面**（不是只在工作列閃），選中的分頁是那個 session 的分頁\n- 對**正在執行中**（分頁開頭是 `◐`／`◑`）的 session 做一次，也能切過去\n- 系統匣圖示按右鍵，也有同樣的「切換到終端機」且能切",
              "spec": {
                "ref": "delta.md AC-JUMP-03、AC-JUMP-05、修改後的 AC-OPS-05",
                "quote": "右鍵 → `abc123` 的子選單 →「切換到終端機」：WT 視窗移到最前面，選中的分頁變成第 2 個"
              },
              "risk": "high",
              "riskReason": "整個跳轉功能的地基；「從桌寵點擊後 Windows 允不允許把 WT 帶到前面」AI 只能用模擬條件測，真正點擊沒人驗過",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_OPS_05_session_submenu_order、test_AC_JUMP_03_switch_item_jumps_with_that_sessions_transcript；tests/test_wt_jump.py::test_AC_JUMP_05_status_prefixes_match"
                },
                "agent": {
                  "covered": true,
                  "how": "建出真的 PetWindow 與右鍵選單、對「切換到終端機」呼叫 trigger()：結果 ok，WT 選中 `✳ Cladue mod 區塊修改` 並在最前面；`◐ Claude Code` 也切得到；子選單順序正確"
                }
              },
              "manualOnly": true,
              "manualOnlyReason": "AI 沒辦法真的用滑鼠點桌寵，Windows 只在「剛被使用者點過」的程式允許搶前景；這裡不過，04～06 卡蓋在上面全部白做，而且要等真的用起來才會發現",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "pass",
                "note": "使用者驗收通過",
                "at": "2026-10-09T14:54:54.546Z"
              }
            },
            {
              "id": "click-to-terminal/03-menu-switch-to-terminal/AC-JUMP-04",
              "text": "開**兩個** WT 視窗：A 視窗裡有某個 Claude Code session，B 視窗放最前面。把 A 視窗**最小化**，記下 B 視窗目前選中哪個分頁。對桌寵右鍵 → A 的那個 session →「切換到終端機」。\n\n預期：\n- A 視窗還原、跑到最前面，選中那個 session 的分頁\n- B 視窗選中的分頁沒變",
              "spec": {
                "ref": "delta.md AC-JUMP-04",
                "quote": "第一個 WT 視窗還原並移到最前面……第二個 WT 視窗的分頁選取不變"
              },
              "risk": "medium",
              "riskReason": "本機只有 1 個 WT 視窗，多視窗情境 AI 沒測過",
              "coverage": {
                "auto": {
                  "covered": false,
                  "ref": ""
                },
                "agent": {
                  "covered": true,
                  "how": "單一視窗：最小化後觸發 → 結果 ok、視窗還原、選中目標分頁、成為前景（141～225 ms）"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "要兩個 WT 視窗；錯了一眼就看得出來",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:08.835Z"
              }
            },
            {
              "id": "click-to-terminal/03-menu-switch-to-terminal/AC-JUMP-06",
              "text": "在某個 Claude Code 分頁輸入 `/rename 跳轉測試`，等分頁標題變成新名字後，切到別的分頁，再從桌寵右鍵 → 那個 session →「切換到終端機」。\n\n預期：\n- 切到標題為 `✳ 跳轉測試` 的分頁",
              "spec": {
                "ref": "delta.md AC-JUMP-06",
                "quote": "使用者之後以 `/rename` 改名為 `跳轉功能`……切到 `✳ 跳轉功能` 那個分頁"
              },
              "risk": "medium",
              "riskReason": "AI 只能用假紀錄檔模擬改名，真的 `/rename` 寫進紀錄檔的格式沒實測",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_wt_jump.py::test_AC_JUMP_06_custom_title_overrides_later_ai_title、test_AC_JUMP_06_renamed_title_finds_renamed_tab"
                },
                "agent": {
                  "covered": true,
                  "how": "假紀錄檔依序寫 ai-title → custom-title `iPAS AI 中級戰情室` → ai-title，觸發後選中 `✳ iPAS AI 中級戰情室`"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "要真的執行 `/rename`；錯了很容易看出來",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:11.238Z"
              }
            },
            {
              "id": "click-to-terminal/03-menu-switch-to-terminal/title-and-match-rules",
              "text": "標題擷取與分頁比對規則：只讀紀錄檔最後 1 MB、改名優先、空改名退回自動標題、讀不到當成沒標題；分頁要完全相同或只多一個狀態前綴才算同名（`.env` 不等於 `✳ env`）。",
              "spec": {
                "ref": "delta.md 名詞定義「session 標題」「狀態前綴」「分頁比對」",
                "quote": ""
              },
              "risk": "low",
              "riskReason": "純函式，有大量測試並做過反向確認",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_wt_jump.py（標題規則、1 MB 邊界、AC-JUMP-05／13／14／17／21 共 30 餘組）"
                },
                "agent": {
                  "covered": true,
                  "how": "實測找不到標題／找不到同名分頁／只有開頭相同的標題時都回報 no_title／no_match，且前景視窗與選中分頁都沒被動到"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:12.888Z"
              }
            },
            {
              "id": "click-to-terminal/03-menu-switch-to-terminal/background-and-non-windows",
              "text": "跳轉在背景執行緒進行，不卡桌寵；非 Windows 系統子選單沒有「切換到終端機」。",
              "spec": {
                "ref": "delta.md 名詞定義「跳轉處理不卡桌寵」、AC-JUMP-08（選單部分）",
                "quote": ""
              },
              "risk": "low",
              "riskReason": "有測試並做過反向確認；非 Windows 只能模擬",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_jump_runs_in_background_and_result_returns_on_main_thread、test_jump_errors_are_reported_not_raised、test_AC_JUMP_08_no_switch_item_on_non_windows"
                },
                "agent": {
                  "covered": true,
                  "how": "實際觸發時 trigger() 0.3～2.3 ms 就返回，處理 73～114 ms 期間主執行緒 5 ms 計時器持續跳動 14～21 次"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:13.622Z"
              }
            }
          ],
          "verified": {
            "at": "2026-10-09T22:57:41+08:00",
            "note": "使用者 2026-10-09 匯出結果：必測項（右鍵實切）通過；兩個 WT 視窗、/rename 實測兩項建議項略過"
          }
        },
        {
          "id": "04-jump-failure-hints",
          "title": "04 跳不過去時的提示與保護",
          "items": [
            {
              "id": "click-to-terminal/04-jump-failure-hints/AC-JUMP-14-15-17-18",
              "text": "用 `python set_state.py waiting` 寫一個假 session（它沒有紀錄檔），把 WT 放到別的程式後面。對桌寵右鍵 → 那個假 session →「切換到終端機」。\n\n預期：\n- WT 被叫到最前面，但選中的分頁**不變**\n- 桌寵旁邊出現「找不到這個 session 的分頁」，約 3 秒後自己消失\n- 提示出現期間拖曳桌寵、按右鍵都正常，提示框長得順眼、位置合理\n\n測完用 `python set_state.py clear` 清掉假 session。",
              "spec": {
                "ref": "delta.md AC-JUMP-14、15、17、18",
                "quote": "WT 視窗移到最前面但選中的分頁不變；跳轉提示顯示「找不到這個 session 的分頁」"
              },
              "risk": "medium",
              "riskReason": "「只叫出視窗不選分頁」完全依賴 Windows 讓桌寵搶前景，AI 從背景觸發時被拒；提示框外觀 AI 看不到",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_wt_jump.py::test_AC_JUMP_14_no_title_brings_wt_front_without_selecting、test_AC_JUMP_15_no_match_brings_most_recent_wt_front、test_AC_JUMP_17_*；tests/test_pet.py::test_AC_JUMP_18_hint_disappears_by_itself_and_does_not_block_pet"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台啟動桌寵：假 session、紀錄檔已刪、無同名分頁、`.env` 類比都出現「找不到這個 session 的分頁」且分頁不變；WT 最小化時會被還原成前景；提示約 3 秒消失、不搶前景"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "錯了一眼就看得到、不傷資料",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:22.946Z"
              }
            },
            {
              "id": "click-to-terminal/04-jump-failure-hints/AC-JUMP-13",
              "text": "在 WT 開兩個分頁，都 `/rename` 成同一個名字（例如 `寫週報`）。對桌寵右鍵 → 其中一個 session →「切換到終端機」。\n\n預期：\n- WT 到最前面但選中的分頁不變\n- 提示「有 2 個分頁同名，請手動切換」",
              "spec": {
                "ref": "delta.md AC-JUMP-13",
                "quote": "跳轉提示顯示「有 2 個分頁同名，請手動切換」"
              },
              "risk": "low",
              "riskReason": "邏輯有測試；只差實機撞名情境",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_wt_jump.py::test_AC_JUMP_13_duplicate_tabs_bring_window_front_without_selecting；tests/test_pet.py::test_AC_JUMP_13_to_19_hint_text"
                },
                "agent": {
                  "covered": false,
                  "how": ""
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "要開兩個同名分頁；錯了很容易發現",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:24.371Z"
              }
            },
            {
              "id": "click-to-terminal/04-jump-failure-hints/AC-JUMP-15-16-multi-window",
              "text": "（有空再做）① 開兩個 WT 視窗，用假 session 觸發「切換到終端機」：叫出來的應該是**最近用過**的那個視窗。② 把所有 WT 都關掉再觸發：不切換任何視窗，只出現「找不到這個 session 的分頁」。",
              "spec": {
                "ref": "delta.md AC-JUMP-15、16",
                "quote": "最近使用過的那個 WT 視窗移到最前面……沒有任何 WT 視窗開著：不切換任何視窗"
              },
              "risk": "low",
              "riskReason": "「Z-order 最上層＝最近使用」是推論，本機只有 1 個視窗",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_wt_jump.py::test_AC_JUMP_15_no_match_brings_most_recent_wt_front、test_AC_JUMP_16_no_wt_window_switches_nothing"
                },
                "agent": {
                  "covered": false,
                  "how": ""
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "需要多視窗／關掉全部 WT；錯了只是叫錯視窗",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:26.284Z"
              }
            },
            {
              "id": "click-to-terminal/04-jump-failure-hints/AC-JUMP-19-20-timeout-busy",
              "text": "切換失敗、逾時 3 秒、處理中再觸發：失敗時提示「切換失敗，請手動切換」且不會切到別的分頁；逾時後不再做任何切換動作、不出第二個提示；處理中再觸發被忽略；桌寵關閉時取消背景處理。",
              "spec": {
                "ref": "delta.md AC-JUMP-19、20、名詞定義「逾時後的保證範圍」",
                "quote": ""
              },
              "risk": "medium",
              "riskReason": "牽涉執行緒與時序，但已用測試與實機逾時模擬驗過",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_wt_jump.py::test_AC_JUMP_19_*（取消旗標在每個切換動作前檢查）；tests/test_pet.py::test_AC_JUMP_19_timeout_reports_failed_once_and_cancels_worker、test_AC_JUMP_19_late_result_of_old_jump_does_not_leak_into_new_jump、test_AC_JUMP_20_second_jump_while_busy_is_ignored、test_closing_pet_sets_cancel_flag"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台：跳轉前先卡 3.3 秒 → 第 3.03 秒出現「切換失敗，請手動切換」，晚到結果被丟棄、無第二個提示、分頁沒被切走；處理中第二次觸發被忽略"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者略過",
                "at": "2026-10-09T14:55:27.632Z"
              }
            }
          ],
          "verified": {
            "at": "2026-10-09T22:57:41+08:00",
            "note": "使用者 2026-10-09 匯出結果：4 項全部略過（提示框外觀尚無人工目視，程式與測試已驗）"
          }
        },
        {
          "id": "05-click-dot-to-jump",
          "title": "05 點圓點或清單列直接跳轉",
          "items": [
            {
              "id": "click-to-terminal/05-click-dot-to-jump/AC-JUMP-01-02",
              "text": "紅綠燈版，先切到別的程式（例如瀏覽器）。**左鍵點一下**某個 session 的小圓點；再到右鍵開啟「顯示專案名稱」，點另一個 session 那一列的**文字**。\n\n預期：\n- 每次 WT 都跳到最前面，選中那個 session 的分頁\n- 桌寵位置沒動、沒有出現提示",
              "spec": {
                "ref": "delta.md AC-JUMP-01、02",
                "quote": "左鍵點一下 `abc123` 的小圓點：WT 視窗移到最前面，選中的分頁變成第 2 個；桌寵位置不變，不出現跳轉提示"
              },
              "risk": "medium",
              "riskReason": "AI 用系統滑鼠輸入實測時 WT 本來就在前景，沒驗到「從別的程式前面搶回 WT」",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_JUMP_01_click_dot_jumps_to_that_session、test_AC_JUMP_02_click_row_text_jumps_when_labels_shown"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台、系統層級滑鼠點擊：點圓點 → 結果 ok、切到目標分頁，桌寵不動、設定檔沒寫入；開專案名稱後點文字端也跳轉成功"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "和 03 卡必測項同一個前景問題，那項過了這項通常也過；錯了一眼就看得到",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "pass",
                "note": "使用者驗收通過",
                "at": "2026-10-09T14:57:36.941Z"
              }
            },
            {
              "id": "click-to-terminal/05-click-dot-to-jump/drag-threshold-feel",
              "text": "隨手**輕點**圓點幾次（手會微微晃的那種），再**按住拖**桌寵到別處。\n\n預期：\n- 輕點不會被當成拖曳（桌寵不跑位）\n- 拖曳起步不會覺得卡卡、跳一下\n\n> 注意：規格寫門檻「Windows 預設約 4 px」，但照卡上指定用的 Qt 門檻在你這台是 **10 px**（125% 縮放約 12.5 實體像素）。覺得拖曳起步太鈍，跟我說，再討論要不要改。",
              "spec": {
                "ref": "delta.md 名詞定義「點一下」",
                "quote": "滑鼠移動距離未超過系統的拖曳門檻（Windows 預設約 4 px）。超過門檻才算拖曳。"
              },
              "risk": "low",
              "riskReason": "門檻數字和規格描述不同，只能靠手感判斷",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_OPS_04_move_within_drag_threshold_is_a_click、test_AC_OPS_04_move_just_over_threshold_is_a_drag"
                },
                "agent": {
                  "covered": false,
                  "how": ""
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "手感只有你能判斷",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "pass",
                "note": "使用者驗收通過",
                "at": "2026-10-09T14:56:16.257Z"
              }
            },
            {
              "id": "click-to-terminal/05-click-dot-to-jump/AC-JUMP-07-12-OPS-04-08",
              "text": "拖 30 px 會移動並記住位置、不跳轉；點圓點之間的空隙沒反應；沒有 session 時點灰點沒反應；非 Windows 點了沒反應；動物版點一下不移動、不記位置。",
              "spec": {
                "ref": "delta.md AC-JUMP-07、08、12、修改後的 AC-OPS-04",
                "quote": ""
              },
              "risk": "low",
              "riskReason": "有測試並做過反向確認，主要情境也用真實滑鼠輸入跑過",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_JUMP_07_drag_30px_from_dot_moves_and_saves_without_jump、test_AC_OPS_04_click_outside_dots_does_nothing、test_AC_JUMP_12_grey_dot_without_session_does_nothing、test_AC_JUMP_08_click_on_non_windows_does_nothing、test_animal_theme_click_does_not_move_or_save"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台系統滑鼠：拖 30 px → 桌寵右移 30 px、pos 記新位置、未跳轉；點空隙、點灰點都沒反應"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "pass",
                "note": "使用者驗收通過",
                "at": "2026-10-09T14:56:19.894Z"
              }
            }
          ],
          "verified": {
            "at": "2026-10-09T22:57:41+08:00",
            "note": "使用者 2026-10-09 匯出結果：3 項全部通過（含拖曳門檻 10 px 手感 OK）"
          }
        },
        {
          "id": "06-click-wolf-to-jump",
          "title": "06 點小狼跳到最需要注意的 session",
          "items": [
            {
              "id": "click-to-terminal/06-click-wolf-to-jump/AC-JUMP-09-10-rule",
              "text": "**請驗算挑選規則**（不用操作，看表判斷對不對）。規則：照 waiting → done → working → thinking 的順序，找第一個有 session 的狀態；同狀態挑**首次出現最早**的；全部 idle 就不跳。\n\n| 情境 | session（狀態，首次出現） | 程式挑的 |\n|---|---|---|\n| 1 | A（working，100）、B（waiting，200）、C（waiting，300） | **B** |\n| 2 | A（thinking，100）、B（done，200） | **B** |\n| 3 | A（idle）、B（working 但 601 秒沒更新 → 逾時轉 idle）、C（done 但 1801 秒沒更新 → 逾時轉 idle） | **不跳** |\n\n預期：三個答案都符合你心中「最需要我處理的那個」。",
              "spec": {
                "ref": "delta.md AC-JUMP-09、10、11",
                "quote": "切到 B 的分頁（狀態最需要注意者中首次出現最早的）"
              },
              "risk": "high",
              "riskReason": "排序與逾時規則屬業務規則（紅線 2），AI 只能說測試通過，不能宣告算對",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_JUMP_09_wolf_target_is_earliest_of_most_urgent_state、test_AC_JUMP_10_wolf_target_follows_waiting_done_working_thinking_order、test_AC_JUMP_11_wolf_target_none_when_busy_sessions_timed_out"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台系統滑鼠點小狼：情境 1、2 都只觸發 B；情境 3 與沒有 session 點了無反應、無提示"
                }
              },
              "manualOnly": true,
              "manualOnlyReason": "紅線 2：涉及時間排序與逾時規則，必須由你驗算；看表即可，約 1 分鐘",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "pass",
                "note": "使用者驗收通過",
                "at": "2026-10-09T14:56:56.824Z"
              }
            },
            {
              "id": "click-to-terminal/06-click-wolf-to-jump/real-click-wolf",
              "text": "動物版（`python pet.py` 不帶參數），讓某個 Claude Code session 停在等你批准（小狼變紅），切到別的程式後**左鍵點一下小狼**。\n\n預期：\n- WT 跳到最前面，選中那個等批准的 session 的分頁\n- 桌寵沒移動\n- 全部 session 都閒置時點小狼，畫面完全沒動靜",
              "spec": {
                "ref": "delta.md AC-JUMP-09、11",
                "quote": ""
              },
              "risk": "medium",
              "riskReason": "實機跳轉走 03～05 卡同一條流程，但小狼這個入口沒在真的 WT 切過分頁",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_JUMP_09_click_wolf_jumps_to_earliest_waiting、test_AC_JUMP_11_click_wolf_all_idle_or_timed_out_does_nothing"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台點小狼 → 紀錄檔不存在時跳轉結果 no_title 並出提示，證明入口接上整條跳轉流程"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "錯了一眼就看得到",
              "manualSuggested": true,
              "crossEnv": false,
              "result": {
                "status": "pass",
                "note": "使用者驗收通過",
                "at": "2026-10-09T14:57:02.998Z"
              }
            },
            {
              "id": "click-to-terminal/06-click-wolf-to-jump/outside-wolf-non-windows",
              "text": "動物版點小狼以外的位置（含下方小圓點）沒反應；非 Windows 點小狼沒反應。",
              "spec": {
                "ref": "delta.md AC-JUMP-08；06 卡實作備註",
                "quote": ""
              },
              "risk": "low",
              "riskReason": "有測試並做過反向確認",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_animal_click_outside_wolf_does_nothing、test_AC_JUMP_08_click_wolf_on_non_windows_does_nothing"
                },
                "agent": {
                  "covered": true,
                  "how": "真實平台點小狼下方小圓點 → 沒有反應"
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false,
              "result": {
                "status": "skip",
                "note": "使用者未填（AI 已驗過・可略過）",
                "at": "2026-10-09T22:57:41+08:00"
              }
            }
          ],
          "verified": {
            "at": "2026-10-09T22:57:41+08:00",
            "note": "使用者 2026-10-09 匯出結果：必測項（挑選規則驗算）與實點小狼通過"
          }
        },
        {
          "id": "07-animal-dots-to-jump",
          "title": "07 動物版點小圓點或清單列直接跳轉（驗收後補做）",
          "items": [
            {
              "id": "click-to-terminal/07-animal-dots-to-jump/AC-OPS-04-animal",
              "text": "動物版（`python pet.py`），開著至少 2 個 Claude Code session（小狼下方才會有小圓點）。切到別的程式後，**左鍵點一下小狼下方某個小圓點**；再開「顯示專案名稱」，點另一個 session 那一列的文字。\n\n預期：\n- 每次都切到**被點的那個** session 的分頁（不是小狼挑的那個）\n- 桌寵沒移動\n- 點小狼本身仍跳到最需要注意的 session",
              "spec": {
                "ref": "delta.md 修改後的 AC-OPS-04",
                "quote": "點的位置在 session 圓點、清單列或小狼上時……跳轉"
              },
              "risk": "medium",
              "riskReason": "AI 只用 Qt 事件測過，動物版小圓點沒在真實 WT 上點過",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_OPS_04_animal_click_dot_jumps_to_that_session、test_AC_JUMP_02_animal_click_row_text_jumps_when_labels_shown"
                },
                "agent": {
                  "covered": false,
                  "how": ""
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "錯了一眼就看得到",
              "manualSuggested": true,
              "crossEnv": false
            },
            {
              "id": "click-to-terminal/07-animal-dots-to-jump/drag-non-windows-outside",
              "text": "動物版從小圓點拖曳會移動並記位置、不跳轉；非 Windows 點小圓點沒反應；點小狼與小圓點以外的地方沒反應。",
              "spec": {
                "ref": "delta.md AC-JUMP-07、08 的動物版對應",
                "quote": ""
              },
              "risk": "low",
              "riskReason": "與紅綠燈版共用同一段判定，有測試並做過反向確認",
              "coverage": {
                "auto": {
                  "covered": true,
                  "ref": "tests/test_pet.py::test_AC_JUMP_07_animal_drag_from_dot_moves_without_jump、test_AC_JUMP_08_animal_click_dot_on_non_windows_does_nothing、test_animal_click_outside_wolf_and_dots_does_nothing"
                },
                "agent": {
                  "covered": false,
                  "how": ""
                }
              },
              "manualOnly": false,
              "manualOnlyReason": "",
              "manualSuggested": false,
              "crossEnv": false
            }
          ]
        }
      ]
    }
  ]
};
