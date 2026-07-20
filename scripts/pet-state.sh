#!/bin/bash
# 桌寵狀態寫入的單一入口（由 Claude Code hooks 呼叫）。
#
# 每個 Claude Code session 各寫一個狀態檔到 ~/.terminalpet/sessions/<sid>.json，
# 桌寵（pet.py）會掃描整個資料夾、取「最高優先級」的狀態顯示，
# 這樣多個 session 同時跑時才不會互相蓋燈。
#
# 用法（hook 會把 payload 由 stdin 餵進來）：
#     bash pet-state.sh working
#
# 設計重點：
#   - 全程 bash 內建指令解析（read + regex），不 spawn cat/grep/sed/tr。
#     Windows git-bash 上每個外部程式 spawn 約 50–80ms，舊版的管線寫法
#     光這些就吃掉約 400ms，是燈號延遲的主因。
#   - 原子寫入（先寫 tmp 再 mv），避免桌寵讀到寫到一半的檔；
#     mv 是本腳本唯一的外部指令。

state="$1"
[ -z "$state" ] && exit 0

dir="$HOME/.terminalpet/sessions"
[ -d "$dir" ] || mkdir -p "$dir"

# 由 hook 的 stdin JSON 取 session_id；取不到就歸到 default（例如手動測試）。
# -t 2：手動在終端執行、stdin 沒有資料時，最多等 2 秒就放行。
input=""
IFS= read -r -d '' -t 2 input
sid=""
[[ $input =~ \"session_id\"[[:space:]]*:[[:space:]]*\"([^\"]*)\" ]] && sid="${BASH_REMATCH[1]}"
sid="${sid//[!A-Za-z0-9._-]/}"
[ -z "$sid" ] && sid="default"

# 原子寫入
tmp="$dir/.$sid.tmp"
printf '{"state":"%s","ts":%s,"sid":"%s"}' "$state" "$EPOCHSECONDS" "$sid" > "$tmp"
mv -f "$tmp" "$dir/$sid.json"
