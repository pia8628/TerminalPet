---
date: 2026-07-20
model: claude-fable-5
session_id: f34086bb-fa97-4fe1-807a-a43bc030f379
summary: 實測找出燈號殘餘延遲的瓶頸是 hook 腳本內的外部指令 spawn，改寫為純 bash 內建指令後由約 450ms 降至約 95ms
tags: [ai_log, ai_log/個人任務]
---

## 作業摘要
使用者反映 7/10 修正後燈號仍有延遲，並詢問能否照 clawd-on-desk 的方法處理。經確認 clawd-on-desk 的核心方法（hook 直接驅動＋檔案監看、輪詢兜底）在 7/10 已採用；實測後找出殘餘延遲的真正瓶頸是 `pet-state.sh` 內的外部指令管線（cat/grep/sed/tr），在 Windows git-bash 上每個外部程式 spawn 約 50–80ms，整支腳本約 450ms。改寫為純 bash 內建指令（read + regex + 參數展開）後降至約 95ms。

## 執行內容
1. WebFetch 調查 clawd-on-desk 的狀態偵測機制（command hooks 為主、HTTP 權限氣泡、JSONL 日誌輪詢備援），對照本專案現況，確認其核心方法已在 7/10 採用。
2. 實測延遲：空 bash spawn 約 40ms，但 `bash pet-state.sh working` 實測 443–482ms → 鎖定瓶頸為腳本內的外部指令 spawn，而非架構。
3. 改寫 `scripts/pet-state.sh`：stdin 改用內建 `read -d ''` 取代 `cat`；session_id 解析改用 `[[ =~ ]]` regex 取代 grep/head/sed 管線；字元清洗改用 `${sid//[!…]/}` 取代 `tr`；`mkdir` 僅在目錄不存在時執行；保留 `mv` 原子寫入（唯一外部指令）。
4. 執行 `install.py` 部署至 `~/.claude/scripts/pet-state.sh`，重新實測 5 次：75–104ms（約 95ms）。
5. 邊界驗證：無 stdin（手動執行）正確落到 `default`；含 `/`、`$` 等字元的 session_id 正確清洗、無路徑穿越；測試產生的假 session 檔已清理。
6. 確認 ClaudeSetting repo 的 `scripts/pet-state.sh` 經 symlink 已同步更新（其 working tree 顯示 modified，待使用者 commit）。

## 更動檔案
- 修改：`scripts/pet-state.sh`（TerminalPet repo）、`C:\Users\User\.claude\scripts\pet-state.sh`（經 install.py 部署，symlink 連動 `D:\Projects\ClaudeSetting\scripts\pet-state.sh`）
- 新增：本日誌

## 結果
- 狀態：完成
- 產出：hook 端寫入延遲由約 450ms 降至約 95ms；hook 設定（command 路徑）未變，新的 hook 呼叫立即生效，pet.py 與 settings.json 均不需改動、桌寵不需重啟。

## 風險與後續
- TerminalPet 與 ClaudeSetting 兩個 repo 各有未 commit 的 `pet-state.sh` 變更，需使用者確認後提交（ClaudeSetting 另有遠端 3 個新提交待 pull）。
- 評估後不建議照抄 clawd-on-desk 剩餘部分：HTTP push 架構收益有限（讀取端已毫秒級，兜底輪詢最壞僅 250ms），且直接安裝該第三方 Electron app 有供應鏈、權限批准接管、對話內容讀取等風險。
- 進一步可做：加 `PostToolUse → thinking` hook 讓工具結束後燈號更貼近真實狀態（語意精確度，非延遲問題）。
