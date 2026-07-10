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
Claude Code hooks ──純 bash printf 直接寫入──▶ ~/.terminalpet/state.json
                                                        │
                                 pet.py 用 QFileSystemWatcher 監看，檔案一變立即更新
                                 （另有每 1 秒的備援輪詢，負責閒置→睡著的判定）
```

狀態來源由 Claude Code 的 hooks 自動驅動（設定於使用者全域 settings.json）：
UserPromptSubmit→thinking、PreToolUse→working、Notification→waiting、
Stop→done、SessionEnd→sleeping。全部以 `async` 背景執行，不拖慢工具呼叫。

為了降低延遲，hook 不再呼叫 `set_state.py`（省去 Python 直譯器冷啟動的數百毫秒），
改用 bash 內建的 `printf` + `$EPOCHSECONDS` 直接寫 JSON；`set_state.py` 保留給手動測試用：

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

## 在其他電腦部署

hooks 改為純 bash 寫入後已不依賴專案路徑，clone 到哪裡都可以（建議仍統一 `D:\Projects\TerminalPet`）：

```
git clone https://github.com/pia8628/TerminalPet.git D:\Projects\TerminalPet
cd D:\Projects\TerminalPet
pip install -r requirements.txt
```

Claude Code 的桌寵 hooks 設在使用者全域 `settings.json`（隨 ClaudeSetting 同步），
不依賴本專案檔案；沒 clone 這個專案的機器只會多一個 `~/.terminalpet/state.json`，不影響 Claude 運作。
