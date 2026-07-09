---
date: 2026-07-09
model: claude-opus-4-8
session_id: 0d88379c-38d1-4a8f-a0c7-c806598ce9cd
summary: 從零建立 TerminalPet 桌寵，含小狼版與辦公室紅綠燈版，掛上 Claude Code hooks 並建立 GitHub repo
tags: [ai_log, ai_log/個人任務]
---

## 作業摘要
起因是評估要不要裝 GitHub 上的 clawd-on-desk 桌寵，評估後決定自建精簡版。從零打造 TerminalPet：一個透明置頂、監看 Claude Code 狀態的桌面小工具，做出「原創小狼像素版」與「辦公室紅綠燈版」兩種外觀，並透過 Claude Code hooks 自動驅動狀態、建立獨立 GitHub repo。

## 執行內容
1. 評估 clawd-on-desk：體質尚可（5.2k star）但要全域鍵盤 hook、讀 ~/.claude、匿名作者，判定為療癒型非剛需，且螃蟹美術為版權保留，決定自建。
2. 設計架構：`set_state.py` 寫狀態到 `~/.terminalpet/state.json`，`pet.py`（PySide6）每 0.5 秒輪詢並更新外觀，狀態由 Claude Code hooks 驅動。
3. 安裝 PySide6 6.11.1，寫出 `pet.py`（無邊框／置頂／透明／可拖曳／右鍵關閉）與 `set_state.py`，先用 emoji 佔位驗證狀態切換。
4. 用 update-config skill 在全域 settings.json 合併加入 5 個桌寵 hooks（UserPromptSubmit→thinking、PreToolUse→working、Notification→waiting、Stop→done、SessionEnd→sleeping），全部 `async` 背景執行；JSON 驗證通過。（註：ClaudeSetting repo 本次未 commit，使用者要求先不要。）
5. 依使用者需求新增第二外觀「辦公室紅綠燈版」：`python pet.py light`，用 QPainter 直接畫圓點（免圖檔），紅=需要你/黃=思考/綠=在跑或完成/灰=閒置。
6. 建立 `run_pet.bat`、`run_office.bat`（pythonw 啟動免終端機視窗）與 README。
7. 將專案初始化為 git repo，設定 git 身分（global），首次 commit 後推上使用者建立的 `github.com/pia8628/TerminalPet`（分支 main），並補 requirements.txt 與多機器部署說明。
8. 生成原創小狼像素圖：與使用者討論定案（像素風、Claude 橘、Q 版圓身、大眼）→ 用 blog-draw-img 的 gpt-image-2 生 1 張五連拍 sprite sheet（gpt-image-2 不支援透明背景，改用洋紅色鍵背景，low 品質 1024×1024）。
9. 用 Pillow 去背（洋紅→透明）＋波谷切割成 5 張 `wolf_*.png`，改 `pet.py` 動物版載入 PNG 顯示（缺圖退回 emoji），commit & push。
10. 清除一次性生圖／切圖腳本（scratchpad）。

## 更動檔案
- 新增（TerminalPet repo）：`pet.py`、`set_state.py`、`run_pet.bat`、`run_office.bat`、`README.md`、`requirements.txt`、`.gitignore`、`assets/wolf_{thinking,working,waiting,done,sleeping}.png`、`assets/_wolf_sheet.png`
- 修改：`D:\Projects\ClaudeSetting\settings.json`（加入 5 個桌寵 hooks；**尚未 commit**）
- 新增（本檔）：`_ai_log/2026-07-09_terminalpet_mvp.md`

## 結果
- 狀態：完成（兩種外觀皆實測可啟動並正確切換狀態；GitHub repo 已推送，3 個 commit）
- 產出：可運作的桌寵 MVP，GitHub repo `pia8628/TerminalPet`

## 風險與後續
- **ClaudeSetting hooks 未 commit**：本機 hooks 已在檔案中，開新 session 即生效；其他機器要等使用者 commit & push ClaudeSetting 才會同步。
- **hooks 需新 session 生效**：本對話開始時尚無這些 hook，需重開 session 或開一次 /hooks 重載。
- hook 內寫死路徑 `D:/Projects/TerminalPet`；方案 A 要求各機統一 clone 到此路徑，否則該台 hook 靜默略過（async，不影響 Claude 運作）。
- 後續可做：小狼 2 格輪播動畫（需再生 1 張圖）、開機自動啟動。
