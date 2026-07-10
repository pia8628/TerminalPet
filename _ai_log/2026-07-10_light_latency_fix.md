---
date: 2026-07-10
model: claude-fable-5
session_id: dc54b521-b6d8-42cf-8e9f-d96930782319
summary: 參考 clawd-on-desk 優化燈號延遲，改用檔案監看與純 bash hook，延遲從約一秒降至近乎即時
tags: [ai_log, ai_log/個人任務]
---

## 作業摘要
使用者反映燈號切換有延遲。參考 clawd-on-desk（Electron 桌寵）的「hook 直接驅動、輪詢僅為 fallback」設計，將 TerminalPet 的讀取端改為 QFileSystemWatcher 即時監看、寫入端 hooks 改為純 bash 寫入，端對端延遲從約 0.5–1 秒降到毫秒級。

## 執行內容
1. 分析延遲來源：hook 端 bash + Python 直譯器冷啟動約 150–450ms，加上 pet.py 每 500ms 輪詢平均再加 250ms。
2. pet.py 加入 QFileSystemWatcher 監看 `~/.terminalpet/`（目錄＋檔案雙監看，Windows 上檔案被覆寫後自動補回監看清單），檔案一變立即刷新，並在 100ms 後補讀一次避免讀到寫入中的檔案。
3. 輪詢降為每 1 秒備援（負責閒置逾時→sleeping 的判定）；`read_state` 遇 JSON 解析失敗改為保持現狀，避免讀到半寫檔案時閃灰燈。
4. 全域 settings.json（實體檔在 `D:\Projects\ClaudeSetting\settings.json`）五個桌寵 hooks 改為純 bash：`printf '{"state":"…","ts":%s}' "$EPOCHSECONDS" > ~/.terminalpet/state.json`，不再呼叫 Python；`set_state.py` 保留供手動測試。
5. 以 offscreen 模式端對端驗證：兩次狀態切換均在 150ms 內被桌寵接收（含測試腳本自身 100ms 等待）；`jq` 驗證 settings.json 語法、`py_compile` 驗證 pet.py。
6. 更新 README 的運作方式與多機部署說明（hooks 已不依賴專案路徑）。

## 更動檔案
- 修改：`pet.py`、`README.md`、`D:\Projects\ClaudeSetting\settings.json`（桌寵五個 hooks）
- 新增：本日誌

## 結果
- 狀態：完成
- 產出：燈號延遲由「hook 冷啟動＋輪詢」的約 0.5–1 秒降為監看驅動的毫秒級；hooks 不再依賴 TerminalPet 專案路徑，未 clone 的機器也能正常運作。

## 風險與後續
- hook 設定變更需 Claude Code 重新載入 settings（重啟或開一次 `/hooks`）才生效；pet.py 需重新啟動才會用新的監看邏輯。
- settings.json 的變更在 ClaudeSetting repo 中尚未 commit，需使用者確認後提交同步到其他機器。
- 進一步可做：clawd-on-desk 的 single instance lock 與位置記憶（重啟後回到上次拖曳位置）。
