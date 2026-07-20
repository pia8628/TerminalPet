# TerminalPet

監看 Claude Code 狀態的桌面小工具。一個透明、置頂的小視窗，
會依 Claude Code 目前在做什麼切換外觀——即使終端機縮到背景，也能瞄一眼知道進度。

## 兩種外觀

| 啟動方式 | 外觀 | 適用 |
|----------|------|------|
| `run_pet.bat` | 動物版（原創小狼像素圖） | 個人、療癒 |
| `run_office.bat` | 紅綠燈版（小圓點） | 辦公室、低調 |

也可用指令啟動：
```
python pet.py          # 動物版
python pet.py light    # 紅綠燈版
```

## 狀態對應

| 狀態 | 動物版 | 紅綠燈版 | 意思 |
|------|--------|----------|------|
| thinking | <img src="assets/wolf_thinking.png" width="60" alt="thinking"> | 🟡 黃 | 思考／處理中 |
| working | <img src="assets/wolf_working.png" width="60" alt="working"> | 🟢 綠 | 自己在跑 |
| waiting | <img src="assets/wolf_waiting.png" width="60" alt="waiting"> | 🔴 紅 | **需要你介入**（等批准） |
| done | <img src="assets/wolf_done.png" width="60" alt="done"> | 🟢 綠 | 完成 |
| sleeping | <img src="assets/wolf_sleeping.png" width="60" alt="sleeping"> | ⚫ 灰 | 閒置（超過 120 秒沒更新） |

## 運作方式

```
Claude Code hooks ──呼叫 scripts/pet-state.sh──▶ ~/.terminalpet/sessions/<session_id>.json
（每個 session 各一檔，原子寫入）                              │
                                       pet.py 掃整個 sessions/ 資料夾，
                                       取「優先級最高」的狀態顯示
                                       （waiting > working > thinking > done > sleeping）
                                       每 250ms 輪詢一次，另有 QFileSystemWatcher 加速偵測
```

狀態來源由 Claude Code 的 hooks 自動驅動（設定於使用者全域 settings.json）：
UserPromptSubmit→thinking、PreToolUse→working、Notification→waiting、
Stop→done、SessionEnd→sleeping。全部以 `async` 背景執行，不拖慢工具呼叫。

### 多 session

多個 Claude Code session 同時跑時，各自的 hook 會依 payload 裡的 `session_id`
寫到自己專屬的檔案，不會互相蓋燈。桌寵永遠顯示「優先級最高」的狀態，
`waiting`（有 session 在等你核准）一定蓋過其他狀態，避免漏看。
超過 120 秒沒更新的 session 視為睡著；超過 1 小時沒更新的 session 檔會被清掉。

### 手動測試

`set_state.py` 是給手動測試用的小工具，會寫一個名為 `manual` 的假 session：

```
python set_state.py waiting   # 手動切狀態，測試桌寵反應
```

## 操作

- **拖曳**：左鍵按住拖動
- **關閉**：右鍵 →「關閉桌寵」

## 待辦

- [x] 動物版換成自製原創小狼像素圖（`assets/wolf_*.png`，橘色 Q 版，版權自有）
- [ ] 可考慮加入開機自動啟動
- [ ] 進階：小狼改 2 格輪播做出動畫感

## 依賴

- Python 3.12+
- PySide6（`pip install -r requirements.txt`）
- Git for Windows（hooks 是 bash 腳本，需要 Git Bash 才能執行；有裝 git 就有）
- Claude Code 建議用較新版本（紅燈用到 Notification 的通知類型 matcher，舊版不支援時紅燈不會亮，其他燈不受影響）

## 安裝 / 在其他電腦部署

不同使用者（不同 `~/.claude` 路徑）都可以用同一支腳本安裝，不用手動改 JSON：

```
git clone https://github.com/pia8628/TerminalPet.git D:\Projects\TerminalPet
cd D:\Projects\TerminalPet
pip install -r requirements.txt
python install.py            # 把桌寵 hooks 併入 ~/.claude/settings.json
python install.py --dry-run  # 只想先看看會改什麼，不實際寫入
```

`install.py` 只會動 `hooks` 區塊裡桌寵相關的那幾條，不影響 `permissions`、
`guard-tool.sh`、`statusLine` 等其他既有設定；重複執行是安全的（幂等），
之後這份腳本有更新，重跑一次就會同步。

裝完（或更新 hooks 後）要**重啟 Claude Code session**（或開一次 `/hooks`）
新的 hooks 設定才會生效；桌寵本身（pet.py）隨時可以重開，不用等。

沒 clone 這個專案、也沒跑過 `install.py` 的機器，桌寵 hooks 不會生效，
但完全不影響 Claude Code 本身運作。
