# 06-點小狼跳到最需要注意的 session

**做完能 demo 什麼**：動物版左鍵點一下小狼，就切到「最需要注意」的那個 session 的分頁（依 waiting → done → working → thinking 的順序，同一種狀態挑最早出現的）；所有 session 都是 idle 或沒有 session 時，點了沒有任何反應。

**Blocked by**：05-點圓點或清單列直接跳轉

**狀態**：待做

**檢查點**：否

## 規格依據

- US-JUMP-02
- AC-JUMP-09、AC-JUMP-10、AC-JUMP-11

## 驗收條件

- [ ] AC-JUMP-09（成功）：Given 動物版，A（working，首次出現 100）、B（waiting，200）、C（waiting，300），都有同名分頁 → When 左鍵點一下小狼 → Then 切到 B 的分頁
- [ ] AC-JUMP-10（成功）：Given 動物版，A（thinking，100）、B（done，200） → When 點一下小狼 → Then 切到 B 的分頁
- [ ] AC-JUMP-11（邊界）：Given 動物版，所有 session 都顯示為 idle（含逾時轉 idle 者）或沒有 session → When 點一下小狼 → Then 沒有任何反應：不切換視窗、不出現提示
- [ ] 技術：挑選目標 session 的規則寫成純函式，用假資料寫進 `tests/test_pet.py`
- [ ] 技術：既有測試與 lint 全綠

## 驗證證據

（**施工完成的當下就填**。`/dev-verify-spec` 會拿這一節產人工驗收清單，決定哪些項目要優先花使用者的時間。
找不到就誠實留空——事後補寫推測會讓使用者以為某個行為有人驗過，直接害他漏測。）

**自動化測試覆蓋**：
- 

**AI 實際操作驗過**：
- 

**AI 驗不了、必須人工看的**：
- 

**可能因環境而異的行為**：
- 

## 實作備註

（實作 session 中發現的事寫這裡；延後處理的項目必須同步記進 `專案進度追蹤.md`。）

