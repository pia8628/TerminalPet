# TerminalPet 系統規格（SPEC）

> 本檔是「系統現在做什麼」的唯一真相總帳。
> 只寫**行為**（系統對使用者做什麼），不寫**實作**（用什麼套件、資料表怎麼設計）。
> 每次功能變更由 `/dev-spec` 產出 delta，經 `/dev-verify-spec` 驗收後合併進本檔。
> 新的 AI session 開發前應先讀本檔，掌握系統全貌。
>
> **編號規則**（任務卡、測試、驗收 Hub 都靠它對帳，不可省）：
> - 模組代號：2～5 個大寫英文字母（如 AUTH、CART）
> - User Story：`US-模組代號-兩位數流水號`（如 US-HOOK-01）
> - 驗收情境：`AC-模組代號-兩位數流水號`（如 AC-HOOK-01），每條都標註它屬於哪個 US、是成功還是錯誤／邊界情境
> - 編號只增不改：條文作廢時保留編號並標「已移除」，不要重排

## 版本紀錄

| 日期 | 變更摘要 | 來源 |
|------|----------|------|
| 2026-10-09 | 初版（v1）：盤點制度導入前已上線的既有行為（以程式碼實際行為為準），另列盤點疑點 | 首次開發（補記錄；使用者決定不送 Codex 審查） |

## 全域規則

- **盤點原則**：v1 條文照程式碼的實際行為記錄。與 README 不一致或疑似不合理之處列在文末「盤點時發現的疑點」，在另開 change 處理前，以本檔條文為準。
- **狀態值**：session 狀態只有五種，依「需要你注意的程度」由高到低：`waiting`（等你處理）＞ `done`（完成）＞ `working`（執行中）＞ `thinking`（思考中）＞ `idle`（閒置）。`end` 是「刪除該 session」的指令，不是狀態值。
- **燈號顏色**：waiting 紅、done 藍、working 綠、thinking 黃、idle 灰。
- **單向資料流**：Claude Code hooks 寫入每個 session 的狀態檔（`~/.terminalpet/sessions/` 底下，一個 session 一個檔）；桌寵只讀取與顯示，只會刪除狀態檔（過期清理、使用者手動移除），不會建立或改寫狀態檔。
- **不拖累 Claude Code**：所有 hooks 都以非同步方式執行；寫入端出任何狀況，Claude Code 的工具呼叫都不會被擋住或變慢。桌寵沒開時，hooks 照常寫檔，不影響 Claude Code。
- **時間基準**：「經過時間」一律以秒計，「最後更新時間」指該 session 最後一次被 hook 寫入的時間。
- **反應時間**：狀態檔變動後，桌寵畫面在 0.25 秒內反映。

## 模組：狀態寫入（代號：HOOK）

### User Stories

- **US-HOOK-01**：身為 Claude Code 使用者，我要每個 session 的動態（開始、思考、跑工具、等批准、完成、結束）自動記錄成該 session 的狀態，才能不必盯著每個終端機
- **US-HOOK-02**：身為同時開多個 session 的使用者，我要每個 session 的狀態檔帶有可辨識的專案名稱與路徑，才能分得出哪顆燈是哪個專案
- **US-HOOK-03**：身為使用者，我要幾乎同時發生的事件不會互相蓋掉，才能確保「等你批准」的紅燈不會被晚到的事件吃掉

### 行為規則（驗收情境）

事件與狀態對應表：

| Claude Code 事件 | 寫入狀態 | 備註 |
|------------------|----------|------|
| SessionStart | idle | |
| UserPromptSubmit | thinking | |
| PreToolUse | working | 工具為 AskUserQuestion 或 ExitPlanMode 時改寫 waiting |
| PostToolUse | working | |
| PermissionRequest | waiting | |
| Notification | waiting | 只有 permission_prompt、elicitation_dialog、agent_needs_input 三種通知會觸發 |
| Stop | done | |
| SessionEnd | （刪除該 session 的狀態檔） | |

- **AC-HOOK-01**（US-HOOK-01，成功）
  - Given：session `abc123` 目前沒有狀態檔
  - When：該 session 觸發 SessionStart
  - Then：`sessions/abc123.json` 出現，狀態為 idle
- **AC-HOOK-02**（US-HOOK-01，成功）
  - Given：session `abc123` 狀態為 thinking
  - When：觸發 PreToolUse，工具名稱為 AskUserQuestion（或 ExitPlanMode）
  - Then：狀態變成 waiting；工具名稱為其他工具（如 Bash）時，狀態變成 working
- **AC-HOOK-03**（US-HOOK-01，成功）
  - Given：session `abc123` 有狀態檔
  - When：觸發 SessionEnd
  - Then：`sessions/abc123.json` 被刪除
- **AC-HOOK-04**（US-HOOK-01，邊界）
  - Given：session `abc123` 狀態為 done
  - When：觸發 Notification，類型為 idle_prompt（閒置 60 秒提醒）
  - Then：狀態檔內容不變，仍為 done，不會亮紅燈
- **AC-HOOK-05**（US-HOOK-01，邊界）
  - Given：舊版設定仍以 `sleeping` 呼叫寫入端
  - When：寫入端收到 sleeping
  - Then：比照 end，刪除該 session 的狀態檔
- **AC-HOOK-06**（US-HOOK-01，錯誤）
  - Given：任何狀態
  - When：寫入端被呼叫時沒有帶狀態參數
  - Then：不建立、不修改任何狀態檔，以結束碼 0 離開
- **AC-HOOK-07**（US-HOOK-01，錯誤）
  - Given：任何狀態
  - When：寫入端收到不在五種狀態內的值，例如 `workng`
  - Then：狀態檔照樣寫入 `workng`，桌寵把它當成 idle 顯示成灰燈（見疑點 2）
- **AC-HOOK-08**（US-HOOK-01，邊界）
  - Given：手動在終端機執行寫入端，stdin 沒有任何資料
  - When：執行 `bash pet-state.sh working`
  - Then：最多等 2 秒後寫入名為 `default` 的 session，狀態為 working
- **AC-HOOK-09**（US-HOOK-02，成功）
  - Given：hook 資料的工作目錄是 `D:\Projects\TerminalPet\`
  - When：觸發任一會寫入狀態的事件
  - Then：狀態檔的專案名稱為 `TerminalPet`，路徑記為 `D:/Projects/TerminalPet`（反斜線轉正斜線、去掉結尾斜線）
- **AC-HOOK-10**（US-HOOK-02，邊界）
  - Given：hook 資料沒有工作目錄
  - When：觸發會寫入狀態的事件
  - Then：專案名稱改用 session 代號，路徑為空字串
- **AC-HOOK-11**（US-HOOK-02，錯誤）
  - Given：hook 資料沒有 session_id
  - When：觸發會寫入狀態的事件
  - Then：寫進名為 `default` 的 session；所有缺 session_id 的事件都共用這一顆燈（見疑點 3）
- **AC-HOOK-12**（US-HOOK-02，邊界）
  - Given：hook 資料的 session_id 含有英數字、`.`、`_`、`-` 以外的字元，例如 `a/b:c`
  - When：觸發會寫入狀態的事件
  - Then：這些字元被拿掉，狀態檔名為 `abc.json`
- **AC-HOOK-13**（US-HOOK-03，成功）
  - Given：session `abc123` 在時間 100.0 第一次出現，狀態 working，進入 working 的時間為 100.0
  - When：時間 160.0 再觸發 PostToolUse（working），時間 200.0 觸發 Stop（done）
  - Then：160.0 那次寫入後，進入目前狀態的時間仍為 100.0；200.0 寫入後狀態為 done、進入目前狀態的時間為 200.0；首次出現時間始終為 100.0
- **AC-HOOK-14**（US-HOOK-03，邊界）
  - Given：session `abc123` 狀態檔最後更新時間為 100.500000，狀態 waiting
  - When：一個觸發於 100.400000 的 working 事件較晚才執行到寫入
  - Then：該事件被放棄，狀態檔仍為 waiting，最後更新時間仍為 100.500000

## 模組：狀態判定（代號：SESS）

### User Stories

- **US-SESS-01**：身為使用者，我要很久沒動靜的 session 自動轉成閒置，才能不被中斷或已離開的 session 誤導
- **US-SESS-02**：身為使用者，我要已經不存在的 session 自動從清單消失，才能不必手動清理終端機直接關掉留下的燈
- **US-SESS-03**：身為使用者，我要 session 的順序固定、同專案的多個 session 有編號，才能每次都在同一個位置找到同一個 session
- **US-SESS-04**：身為使用者，我要一眼看到所有 session 中最需要我注意的狀態，才能決定要不要去處理

### 行為規則（驗收情境）

逾時與清除規則（「經過時間」＝現在減去最後更新時間）：

| 原始狀態 | 經過時間超過 | 顯示成 | 狀態檔被刪除的時機 |
|----------|-------------|--------|--------------------|
| thinking、working | 600 秒（10 分） | idle | 經過時間超過 10800 秒（3 小時） |
| done | 1800 秒（30 分） | idle | 經過時間超過 10800 秒（3 小時） |
| idle | — | idle | 經過時間超過 10800 秒（3 小時） |
| waiting | 不轉換 | waiting | 經過時間超過 43200 秒（12 小時，見疑點 1） |
| 不認得的值 | — | idle | 經過時間超過 10800 秒（3 小時） |

- **AC-SESS-01**（US-SESS-01，成功）
  - Given：session 狀態 working，最後更新時間在 601 秒前
  - When：桌寵讀取狀態
  - Then：該 session 顯示為 idle（灰燈）
- **AC-SESS-02**（US-SESS-01，邊界）
  - Given：session 狀態 working，最後更新時間剛好在 600 秒前
  - When：桌寵讀取狀態
  - Then：仍顯示為 working（綠燈）；要超過 600 秒才轉灰
- **AC-SESS-03**（US-SESS-01，成功）
  - Given：session 狀態 done，最後更新時間在 1801 秒前
  - When：桌寵讀取狀態
  - Then：顯示為 idle；1800 秒（含）以內仍顯示 done（藍燈）
- **AC-SESS-04**（US-SESS-01，邊界）
  - Given：session 狀態 waiting，最後更新時間在 5 小時前
  - When：桌寵讀取狀態
  - Then：仍顯示為 waiting（紅燈），不轉灰
- **AC-SESS-05**（US-SESS-02，成功）
  - Given：session 狀態 working，最後更新時間在 10801 秒前
  - When：桌寵讀取狀態
  - Then：該 session 的狀態檔被刪除，不出現在清單
- **AC-SESS-06**（US-SESS-02，邊界）
  - Given：session 狀態 waiting，最後更新時間分別在 43200 秒前與 43201 秒前
  - When：桌寵讀取狀態
  - Then：43200 秒那個仍顯示紅燈；43201 秒那個狀態檔被刪除（見疑點 1）
- **AC-SESS-07**（US-SESS-02，錯誤）
  - Given：桌寵上一次成功讀到 session `abc123`，這一次讀取時該檔案內容不完整（寫到一半）
  - When：桌寵讀取狀態
  - Then：沿用上一次讀到的內容顯示，燈不會短暫消失；該檔不被刪除
- **AC-SESS-08**（US-SESS-02，錯誤）
  - Given：某狀態檔從未被成功讀到過，且內容不是合法格式（或最後更新時間不是數字）
  - When：桌寵讀取狀態
  - Then：該檔不顯示、不刪除，其他 session 照常顯示
- **AC-SESS-09**（US-SESS-03，成功）
  - Given：三個 session，首次出現時間依序為 B（100）、A（200）、C（300）
  - When：桌寵顯示清單
  - Then：順序為 B、A、C，之後狀態變化也不改變順序；首次出現時間相同時依 session 代號排序
- **AC-SESS-10**（US-SESS-03，成功）
  - Given：兩個 session 的專案名稱都是 `TerminalPet`，首次出現時間 100 與 200；另一個 session 專案名稱 `Blog`
  - When：桌寵顯示清單
  - Then：名稱依序為 `TerminalPet #1`、`TerminalPet #2`；`Blog` 不加編號
- **AC-SESS-11**（US-SESS-03，邊界）
  - Given：狀態檔沒有專案名稱，session 代號為 `0123456789abcdef`
  - When：桌寵顯示清單
  - Then：名稱顯示為 `01234567`（代號前 8 碼）
- **AC-SESS-12**（US-SESS-04，成功）
  - Given：三個 session 狀態分別為 working、done、thinking
  - When：桌寵計算整體狀態
  - Then：整體狀態為 done；只要任一 session 為 waiting，整體狀態就是 waiting
- **AC-SESS-13**（US-SESS-04，邊界）
  - Given：沒有任何 session
  - When：桌寵計算整體狀態
  - Then：整體狀態為 idle

## 模組：顯示（代號：VIEW）

### User Stories

- **US-VIEW-01**：身為個人使用者，我要動物版外觀（小狼顯示整體狀態＋各 session 小燈），才能邊工作邊有療癒感
- **US-VIEW-02**：身為在辦公室的使用者，我要低調的紅綠燈版外觀，才能不引人注目
- **US-VIEW-03**：身為使用者，我要能把燈列展開成「專案名稱＋狀態＋經過時間」清單，才能不用猜哪顆燈是誰
- **US-VIEW-04**：身為使用者，我要紅燈會閃、滑鼠停在燈上有詳細資訊，才能注意到需要處理的 session 並確認細節

### 行為規則（驗收情境）

- 視窗為透明、無邊框、永遠置頂的小視窗，不出現在工作列。

- **AC-VIEW-01**（US-VIEW-01，成功）
  - Given：外觀為動物版，三個 session 狀態為 working、waiting、idle，未開「顯示專案名稱」
  - When：桌寵顯示
  - Then：上方小狼顯示 waiting 的圖，下方一排 3 顆小圓點，依 session 順序為綠、紅、灰
- **AC-VIEW-02**（US-VIEW-01，邊界）
  - Given：外觀為動物版，未開「顯示專案名稱」，只有 1 個 session（或 0 個）
  - When：桌寵顯示
  - Then：只顯示小狼，不畫小圓點；0 個 session 時小狼為睡覺的圖
- **AC-VIEW-03**（US-VIEW-01，錯誤）
  - Given：外觀為動物版，某狀態的小狼圖檔不存在
  - When：整體狀態為該狀態
  - Then：改顯示對應的表情符號組合（如 waiting 為 🐺❗、idle 為 🐺💤），程式不中止
- **AC-VIEW-04**（US-VIEW-02，成功）
  - Given：外觀為紅綠燈版，兩個 session 狀態為 thinking、done
  - When：桌寵顯示
  - Then：一排 2 顆圓點，依序黃、藍，沒有小狼
- **AC-VIEW-05**（US-VIEW-02，邊界）
  - Given：外觀為紅綠燈版，沒有任何 session
  - When：桌寵顯示
  - Then：顯示 1 顆灰色圓點，表示桌寵仍在執行；滑鼠停在上面不跳提示
- **AC-VIEW-06**（US-VIEW-03，成功）
  - Given：開啟「顯示專案名稱」，session `TerminalPet` 狀態 working、進入 working 已 125 秒；session `Blog` 狀態 idle
  - When：桌寵顯示
  - Then：每個 session 一列，前面是對應顏色的小圓點，文字分別為 `TerminalPet  執行中 2 分`、`Blog  閒置`（閒置不顯示經過時間）；動物版時清單在小狼下方
- **AC-VIEW-07**（US-VIEW-03，邊界）
  - Given：開啟「顯示專案名稱」，沒有任何 session
  - When：桌寵顯示
  - Then：紅綠燈版顯示一列「沒有 session」；動物版只顯示睡覺的小狼，不顯示這一列（見疑點 4）
- **AC-VIEW-08**（US-VIEW-03，邊界）
  - Given：某 session 進入目前狀態的經過秒數分別為 0、59、60、3599、3600、3725
  - When：顯示經過時間
  - Then：依序顯示 `剛剛`、`剛剛`、`1 分`、`59 分`、`1 小時 0 分`、`1 小時 2 分`；經過秒數為負數時顯示 `剛剛`
- **AC-VIEW-09**（US-VIEW-04，成功）
  - Given：有 session 狀態為 waiting
  - When：桌寵顯示
  - Then：該 session 的紅燈每 0.5 秒在「全亮」與「半透明」之間切換；其他狀態的燈不閃
- **AC-VIEW-10**（US-VIEW-04，成功）
  - Given：session `TerminalPet` 狀態 done、進入 done 已 300 秒、路徑 `D:/Projects/TerminalPet`
  - When：滑鼠停在它的燈（或清單列）上
  - Then：提示三行：`TerminalPet`、`完成（5 分）`、`D:/Projects/TerminalPet`；路徑為空時只顯示前兩行
- **AC-VIEW-11**（US-VIEW-04，邊界）
  - Given：外觀為動物版
  - When：滑鼠停在小狼上
  - Then：有 session 時列出所有 session 的「名稱  狀態 經過時間」；沒有 session 時顯示「目前沒有 Claude Code session」

## 模組：操作與設定（代號：OPS）

### User Stories

- **US-OPS-01**：身為使用者，我要能拖曳桌寵並記住位置，才能把它放在不擋視線的地方
- **US-OPS-02**：身為使用者，我要從右鍵選單操作 session 與切換設定，才能不必碰任何檔案
- **US-OPS-03**：身為使用者，我要啟動方式簡單且不會重複開出第二隻，才能放心地隨手開啟
- **US-OPS-04**：身為 Windows 使用者，我要能設定開機自動啟動，才能不用每天手動開

### 行為規則（驗收情境）

設定項目與預設值：外觀（預設動物版）、顯示專案名稱（預設關）、桌面通知（預設關）、視窗位置（預設無）。設定在變更當下存檔，下次啟動沿用。

- **AC-OPS-01**（US-OPS-01，成功）
  - Given：桌寵在螢幕上
  - When：用左鍵按住拖到新位置後放開，再關閉並重新啟動桌寵
  - Then：桌寵出現在放開時的位置
- **AC-OPS-02**（US-OPS-01，邊界）
  - Given：上次記住的位置在一台已拔掉的外接螢幕上
  - When：啟動桌寵
  - Then：改放在主螢幕可用範圍的右下角，距右緣與下緣各 40 px
- **AC-OPS-03**（US-OPS-01，邊界）
  - Given：桌寵中心位於螢幕的右下半部
  - When：session 數量變化使桌寵變寬或變高
  - Then：桌寵的右下角位置不動，往左上長；中心在左上半部時則固定左上角
- **AC-OPS-04**（US-OPS-01，邊界）
  - Given：桌寵在螢幕上
  - When：左鍵點一下但沒有移動就放開
  - Then：不更新記住的位置
- **AC-OPS-05**（US-OPS-02，成功）
  - Given：有兩個 session，其中一個有路徑
  - When：在桌寵上按右鍵
  - Then：選單依序為：每個 session 一個子選單（標題含狀態圓點與「名稱  狀態 經過時間」；子選單有「開啟資料夾」〔僅有路徑時〕與「從清單移除」）、「清除閒置的 session」、分隔線、「外觀」（動物版／紅綠燈版，單選）、「顯示專案名稱」、「桌面通知（需要你／完成時）」、「開機自動啟動」〔僅 Windows〕、分隔線、「關閉桌寵」
- **AC-OPS-06**（US-OPS-02，邊界）
  - Given：沒有任何 session
  - When：在桌寵上按右鍵
  - Then：session 區只有一個無法點選的「目前沒有 Claude Code session」，沒有「清除閒置的 session」
- **AC-OPS-07**（US-OPS-02，成功）
  - Given：session `abc123` 在清單中
  - When：點該 session 的「從清單移除」
  - Then：`abc123` 的狀態檔被刪除、燈立即消失；該 session 之後若再觸發 hook，會以新狀態重新出現
- **AC-OPS-08**（US-OPS-02，成功）
  - Given：三個 session，顯示狀態為 idle、idle、waiting
  - When：點「清除閒置的 session」
  - Then：兩個 idle 的狀態檔被刪除，waiting 那個保留
- **AC-OPS-09**（US-OPS-02，成功）
  - Given：外觀為動物版
  - When：右鍵 →「外觀」→「紅綠燈版」
  - Then：立即切換為紅綠燈版，下次啟動仍為紅綠燈版
- **AC-OPS-10**（US-OPS-02，錯誤）
  - Given：設定檔內容損毀，或外觀值不是動物版／紅綠燈版
  - When：啟動桌寵
  - Then：損毀時全部設定回到預設值；外觀值無效時外觀改為動物版；桌寵照常啟動
- **AC-OPS-11**（US-OPS-03，成功）
  - Given：任何設定
  - When：以參數 `light` 或 `office` 啟動（不分大小寫）；或以 `animal`、`pet`、`wolf` 啟動
  - Then：外觀分別為紅綠燈版或動物版，並記住；之後不帶參數啟動沿用該外觀
- **AC-OPS-12**（US-OPS-03，邊界）
  - Given：上次外觀為紅綠燈版
  - When：以不認得的參數啟動，例如 `python pet.py foo`
  - Then：參數被忽略，外觀仍為紅綠燈版
- **AC-OPS-13**（US-OPS-03，錯誤）
  - Given：桌寵已在執行中
  - When：再啟動一次
  - Then：跳出訊息「桌寵已經在執行中。要切換外觀請在桌寵上按右鍵 →「外觀」。」，第二個不會出現，第一個不受影響
- **AC-OPS-14**（US-OPS-03，成功）
  - Given：桌寵在執行中
  - When：右鍵 →「關閉桌寵」
  - Then：桌寵關閉，之後可再次啟動，不會被誤判為「已在執行中」
- **AC-OPS-15**（US-OPS-04，成功）
  - Given：Windows，開機自動啟動未勾選
  - When：勾選「開機自動啟動」，然後登出再登入
  - Then：桌寵自動啟動，沒有跳出終端機視窗，外觀沿用上次設定；取消勾選後再登入則不會自動啟動
- **AC-OPS-16**（US-OPS-04，邊界）
  - Given：非 Windows 系統
  - When：按右鍵開選單
  - Then：選單中沒有「開機自動啟動」這一項

## 模組：桌面通知（代號：NOTI）

### User Stories

- **US-NOTI-01**：身為會切到其他視窗工作的使用者，我要 session 需要我或完成時跳出系統通知，才能不必一直看桌寵

### 行為規則（驗收情境）

- **AC-NOTI-01**（US-NOTI-01，成功）
  - Given：已開啟桌面通知，session `TerminalPet` 狀態為 working
  - When：該 session 變成 waiting
  - Then：跳出警示通知，標題「TerminalPet 需要你處理」、內容「等待批准或回答」，停留 8 秒
- **AC-NOTI-02**（US-NOTI-01，成功）
  - Given：已開啟桌面通知，session `TerminalPet` 狀態為 working
  - When：該 session 變成 done
  - Then：跳出資訊通知，標題「TerminalPet 已完成」、內容「換你了」，停留 5 秒
- **AC-NOTI-03**（US-NOTI-01，成功）
  - Given：桌面通知原本關閉
  - When：右鍵勾選「桌面通知（需要你／完成時）」
  - Then：系統匣出現一顆圓點圖示，顏色為整體狀態的燈色；滑鼠停留顯示「TerminalPet」與各 session 摘要；對它按右鍵出現與桌寵相同的選單。取消勾選後圖示消失、不再跳通知
- **AC-NOTI-04**（US-NOTI-01，邊界）
  - Given：已開啟桌面通知，桌寵尚未啟動時已有一個 waiting、一個 done 的 session
  - When：啟動桌寵
  - Then：不跳任何通知；之後只有狀態「變成」waiting 或 done 時才跳
- **AC-NOTI-05**（US-NOTI-01，邊界）
  - Given：已開啟桌面通知，session 已是 waiting 並跳過一次通知
  - When：該 session 又收到 waiting 事件，或某 session 逾時轉成 idle
  - Then：不跳通知
- **AC-NOTI-06**（US-NOTI-01，邊界）
  - Given：已開啟桌面通知，桌寵執行中
  - When：一個新 session 第一次出現時就是 waiting
  - Then：跳出「需要你處理」通知
- **AC-NOTI-07**（US-NOTI-01，錯誤）
  - Given：系統不支援系統匣
  - When：按右鍵開選單
  - Then：「桌面通知」選項為灰色無法點選，不跳任何通知

## 模組：安裝（代號：INST）

### User Stories

- **US-INST-01**：身為 Claude Code 使用者，我要用 plugin 一鍵裝好 hooks，才能不必動自己的 settings.json
- **US-INST-02**：身為不用 plugin 的使用者，我要一支安裝腳本幫我把 hooks 安全地併進 settings.json，才能不必手改設定也不怕弄壞

### 行為規則（驗收情境）

- **AC-INST-01**（US-INST-01，成功）
  - Given：Claude Code 尚未安裝本 plugin
  - When：執行 `/plugin marketplace add pia8628/TerminalPet` 與 `/plugin install terminalpet@terminalpet`，並重啟 session
  - Then：事件與狀態對應表中的 8 個事件都會寫入狀態檔，使用者的 settings.json 內容不變
- **AC-INST-02**（US-INST-01，邊界）
  - Given：已安裝 plugin，但沒有重啟 Claude Code session
  - When：在既有 session 中操作
  - Then：該 session 不會寫入狀態檔；重啟（或開一次 `/hooks`）後才生效
- **AC-INST-03**（US-INST-02，成功）
  - Given：settings.json 已有其他 hooks 與設定，尚未安裝桌寵 hooks
  - When：執行 `python install.py`
  - Then：寫入端腳本被複製到 `~/.claude/scripts/pet-state.sh`；settings.json 的 8 個事件各多一條桌寵 hook（Notification 帶三種通知類型的篩選）；其他設定與 hooks 不變；寫入前原檔備份為 `settings.json.terminalpet.bak`；最後提示要重啟 session
- **AC-INST-04**（US-INST-02，邊界）
  - Given：已用 `install.py` 安裝過且內容是最新版
  - When：再執行一次 `python install.py`
  - Then：顯示「已是最新狀態，無需變更。」，settings.json 與腳本都不被改寫
- **AC-INST-05**（US-INST-02，邊界）
  - Given：settings.json 裡有舊版桌寵 hook（含已不使用的事件上的桌寵 hook）
  - When：執行 `python install.py`
  - Then：舊版桌寵 hook 在原本位置被替換成新版，已不使用事件上的桌寵 hook 被移除，每個事件只留一條桌寵 hook
- **AC-INST-06**（US-INST-02，成功）
  - Given：任何安裝狀態
  - When：執行 `python install.py --dry-run`
  - Then：列出會做的變更並註明「dry-run，未實際寫入」，settings.json 與腳本都不被改動
- **AC-INST-07**（US-INST-02，成功）
  - Given：已用 `install.py` 安裝
  - When：執行 `python install.py --uninstall`
  - Then：settings.json 中所有桌寵 hook 被移除（某事件只剩空清單時連事件一起移除）、`~/.claude/scripts/pet-state.sh` 被刪除、其他設定不變；`~/.terminalpet/` 資料夾保留並提示可自行刪除
- **AC-INST-08**（US-INST-02，錯誤）
  - Given：settings.json 不是合法的 JSON
  - When：執行 `python install.py`
  - Then：程式以錯誤結束，settings.json 內容不變、不產生備份
- **AC-INST-09**（US-INST-02，錯誤）
  - Given：從不完整的專案資料夾執行，`scripts/pet-state.sh` 不存在
  - When：執行 `python install.py`
  - Then：顯示「錯誤：找不到 …pet-state.sh」並以結束碼 1 離開，不改動任何檔案

## 模組：手動測試工具（代號：TOOL）

### User Stories

- **US-TOOL-01**：身為開發者，我要不開 Claude Code 也能寫入假 session，才能測試桌寵的各種顯示情境
- **US-TOOL-02**：身為開發者，我要一次清掉所有假 session 而不動到真的 session，才能測完放心收拾

### 行為規則（驗收情境）

- **AC-TOOL-01**（US-TOOL-01，成功）
  - Given：沒有假 session
  - When：執行 `python set_state.py waiting`
  - Then：出現名為 `manual` 的 session，狀態 waiting，專案名稱 `manual`
- **AC-TOOL-02**（US-TOOL-01，成功）
  - Given：沒有假 session
  - When：執行 `python set_state.py working --session b --project 另一個專案`
  - Then：出現代號 `manual-b` 的 session（不以 manual 開頭的名稱會自動加上 `manual-` 前綴），狀態 working，專案名稱 `另一個專案`
- **AC-TOOL-03**（US-TOOL-01，成功）
  - Given：`manual-b` 狀態為 working，專案名稱 `另一個專案`
  - When：執行 `python set_state.py done --session b`（不帶 --project）
  - Then：狀態變成 done，專案名稱沿用 `另一個專案`，首次出現時間不變
- **AC-TOOL-04**（US-TOOL-01，成功）
  - Given：`manual-b` 存在
  - When：執行 `python set_state.py end --session b`
  - Then：`manual-b` 的狀態檔被刪除
- **AC-TOOL-05**（US-TOOL-01，錯誤）
  - Given：任何狀態
  - When：執行 `python set_state.py foo`
  - Then：以錯誤結束並列出可用狀態，不建立也不修改任何狀態檔
- **AC-TOOL-06**（US-TOOL-02，成功）
  - Given：有假 session `manual`、`manual-b`，以及真的 session `abc123`
  - When：執行 `python set_state.py clear`
  - Then：`manual` 與 `manual-b` 的狀態檔被刪除，`abc123` 保留
- **AC-TOOL-07**（US-TOOL-02，邊界）
  - Given：沒有任何假 session
  - When：執行 `python set_state.py clear`
  - Then：不報錯，任何狀態檔都不變

## 盤點時發現的疑點

> v1 盤點時發現、與 README 不一致或疑似不合理的現況。上方條文照現況寫；要改的話各自另開 change 走 `/dev-spec`，改之前以上方條文為準。

| # | 現況（對應條文） | 為什麼算疑點 |
|---|------------------|--------------|
| 1 | waiting 紅燈 12 小時沒更新會被清掉（AC-SESS-06） | README 寫 waiting「不會自己逾時」，兩者不一致 |
| 2 | 打錯字的狀態值照樣寫入，桌寵顯示成灰燈（AC-HOOK-07） | 沒有任何提示，看起來像 session 閒置 |
| 3 | 缺 session_id 的事件都寫進 `default` 這一顆燈（AC-HOOK-11） | 多個來源擠在同一顆燈 |
| 4 | 0 個 session 時，紅綠燈版顯示灰燈／「沒有 session」，動物版開了顯示專案名稱也不顯示那一列（AC-VIEW-05、AC-VIEW-07） | 兩種外觀的空狀態處理不一致 |

## Out of Scope（明確不做）

- 打包 exe 與發行流程（PyInstaller、`scripts/build.ps1`）：屬發行作業，不是使用者可觀察的行為，不列入本規格
- Claude Code 用量或費用統計
- 網頁版或手機版
- 用 hooks 以外的方式偵測狀態（讀終端機畫面、解析 log）
- 點子池（尚未實作，之後各自走 `/dev-spec`）：點擊燈號跳到對應終端機視窗、偵測 Claude 程序結束時立即移除、小狼 2 格輪播動畫、`pipx install` 發行

<!-- codex-peer-reviewed: 2026-10-09 rounds=0 verdict=SKIPPED-by-user-v1-backfill -->
