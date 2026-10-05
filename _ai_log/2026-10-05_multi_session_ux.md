---
date: 2026-10-05
model: claude-opus-5-5
summary: 多 session 個別顯示、狀態語意修正、分享友善化（工作清單，完成後補成日誌）
tags: [ai_log, ai_log/個人任務]
---

## 待辦清單

### 狀態語意（hook 端 pet-state.sh）
- [x] 記錄 cwd / 專案名稱，作為 session 標籤
- [x] 記錄 start（首次出現）與 since（進入目前狀態的時間），供排序與「等了幾分鐘」
- [x] ts 改微秒精度，並拒絕「比現有檔案舊」的寫入，避免 async hook 亂序把紅燈蓋掉
- [x] PreToolUse 的 AskUserQuestion / ExitPlanMode 視為 waiting
- [x] SessionEnd 直接刪檔；SessionStart 寫 idle，讓新 session 立刻出現
- [x] macOS bash 3.2 相容（無 EPOCHSECONDS / EPOCHREALTIME 時退回 date）

### 安裝（install.py）
- [x] 新增 SessionStart、PostToolUse 事件
- [x] Notification matcher 補 elicitation_dialog
- [x] --uninstall

### 桌寵（pet.py）
- [x] 每個 session 一個燈（依 start 排序），可切換顯示專案名稱
- [x] 逾時規則分狀態：waiting 不衰減、working/thinking 10 分鐘、done 30 分鐘
- [x] done 改藍色，與 working 區分；waiting 閃爍
- [x] 動物版：小狼顯示最高優先狀態 + 下方 session 燈列
- [x] 滑鼠停留顯示該 session 詳細（名稱、狀態、經過時間）
- [x] 右鍵：切換外觀、顯示名稱、清除閒置 session、開機自動啟動、桌面通知、關閉
- [x] 設定檔 ~/.terminalpet/config.json：位置、外觀、選項
- [x] 單一執行個體（QLockFile）

### 分享
- [x] Claude Code plugin 打包（.claude-plugin/ + hooks/hooks.json）
- [x] README 改寫：安裝、多 session、反安裝
- [x] set_state.py 支援指定 session / 專案名稱，方便測試多 session

### 驗證
- [x] pet-state.sh 邊界測試（亂序、無 stdin、中文路徑、根目錄）
- [x] pet.py offscreen 測試多 session 聚合與逾時
- [x] install.py --dry-run（安裝與 --uninstall 兩種）
- [x] plugin 版 hooks 以 `claude -p --plugin-dir .` 實測（Windows）：idle → thinking → done 正確寫入
- [x] 本機 ~/.claude 的 hooks 更新（install.py 實裝、MACHINES.md 新增待辦，兩 repo 已 commit 未 push）
- [x] 實機試用（使用者確認 OK）
- [x] 授權條款：MIT（著作權人 佳臨 (pia8628)）

## 發現
- 狀態語意問題比延遲更影響使用：waiting 120 秒變灰、done/working 同為綠色、批准後紅燈卡住、done 優先級低於 working 導致多 session 時看不到完成訊號。
- 新舊版 hook 混用時，舊版會用舊格式覆寫，造成 start 重設；更新 hooks 後即消失。
- offscreen 平台沒有字型，截圖要用 windows 平台（grab() 不需顯示視窗）。
- 同類專案參考：Claude Status Bar（macOS，聚合 + 下拉清單）、Claude Usage Monitor for Windows（每 session 一點）、ccmonitor（plugin marketplace 發佈 hooks、可跳 Windows Terminal 分頁）、Claudlet（pipx 發佈的 Python 桌寵）、MyAgents（點擊聚焦終端、process 存活偵測）。
