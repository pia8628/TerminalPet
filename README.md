# TerminalPet

監看 Claude Code 狀態的桌面小工具。一個透明、置頂的小視窗，
會依 Claude Code 目前在做什麼切換外觀——即使終端機縮到背景，也能瞄一眼知道進度。

## 兩種外觀

| 啟動方式 | 外觀 | 適用 |
|----------|------|------|
| `run_pet.bat` | 動物版（螃蟹／小狼 GIF） | 個人、療癒 |
| `run_office.bat` | 紅綠燈版（小圓點） | 辦公室、低調 |

也可用指令啟動：
```
python pet.py          # 動物版
python pet.py light    # 紅綠燈版
```

## 狀態對應

| 狀態 | 動物版 | 紅綠燈版 | 意思 |
|------|--------|----------|------|
| thinking | 🦀💭 | 🟡 黃 | 思考／處理中 |
| working | 🦀⚙️ | 🟢 綠 | 自己在跑 |
| waiting | 🦀❗ | 🔴 紅 | **需要你介入**（等批准） |
| done | 🦀✅ | 🟢 綠 | 完成 |
| sleeping | 🦀💤 | ⚫ 灰 | 閒置（超過 120 秒沒更新） |

## 運作方式

```
Claude Code hooks ──呼叫──▶ set_state.py ──寫入──▶ ~/.terminalpet/state.json
                                                        │
                                        pet.py 每 0.5 秒讀取並更新外觀
```

狀態來源由 Claude Code 的 hooks 自動驅動（設定於使用者全域 settings.json）：
UserPromptSubmit→thinking、PreToolUse→working、Notification→waiting、
Stop→done、SessionEnd→sleeping。全部以 `async` 背景執行，不拖慢工具呼叫。

## 操作

- **拖曳**：左鍵按住拖動
- **關閉**：右鍵 →「關閉桌寵」

## 待辦

- [ ] 動物版目前用 emoji 佔位，之後換成自製的螃蟹／小狼 GIF（版權需自有）
- [ ] 可考慮加入開機自動啟動

## 依賴

- Python 3.12+
- PySide6（`pip install -r requirements.txt`）

## 在其他電腦部署

各機器統一 clone 到相同路徑 `D:\Projects\TerminalPet`（Claude Code hooks 寫死此路徑）：

```
git clone https://github.com/pia8628/TerminalPet.git D:\Projects\TerminalPet
cd D:\Projects\TerminalPet
pip install -r requirements.txt
```

Claude Code 的桌寵 hooks 設在使用者全域 `settings.json`（隨 ClaudeSetting 同步），
路徑一致時各機通用；若某台沒 clone 這個專案，hook 會靜默略過、不影響 Claude 運作。
