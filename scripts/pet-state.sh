#!/bin/bash
# 桌寵狀態寫入的單一入口（由 Claude Code hooks 呼叫）。
#
# 每個 Claude Code session 各寫一個狀態檔到 ~/.terminalpet/sessions/<sid>.json，
# 桌寵（pet.py）會掃描整個資料夾，每個 session 各顯示一個燈。
#
# 用法（hook 會把 payload 由 stdin 餵進來）：
#     bash pet-state.sh working
#
# 狀態：idle | thinking | working | waiting | done | end（end = 刪除該 session）
#
# 設計重點：
#   - 全程 bash 內建指令解析（read + regex），不 spawn cat/grep/sed/tr。
#     Windows git-bash 上每個外部程式 spawn 約 50–80ms，是燈號延遲的主因。
#   - 原子寫入（先寫 tmp 再 mv），避免桌寵讀到寫到一半的檔；
#     mv 是一般情況下唯一的外部指令。
#   - hooks 都是 async，兩個幾乎同時觸發的 hook（例如 PreToolUse 與
#     Notification）可能亂序寫入，所以用微秒時間戳記，比現有檔案舊就放棄寫入，
#     避免「等你批准」的紅燈被晚到的 working 蓋掉。

state="$1"
[ -z "$state" ] && exit 0

dir="$HOME/.terminalpet/sessions"
[ -d "$dir" ] || mkdir -p "$dir"

# 盡早取時間：代表 hook 觸發的時間點，而非腳本跑完的時間點。
# bash 5 有 EPOCHREALTIME（微秒）；macOS 內建 bash 3.2 沒有，退回 date。
now="$EPOCHREALTIME"
[ -z "$now" ] && now="$(date +%s)"
now="${now/,/.}"  # 部分語系的小數點是逗號

# 時間字串 → 整數微秒，供比較先後
to_us() {
    local s="${1%%.*}" f=""
    [[ $1 == *.* ]] && f="${1#*.}"
    f="${f}000000"
    f="${f:0:6}"
    REPLY="$s$f"
}

# 由 hook 的 stdin JSON 取欄位；取不到就歸到 default（例如手動測試）。
# -t 2：手動在終端執行、stdin 沒有資料時，最多等 2 秒就放行。
input=""
IFS= read -r -d '' -t 2 input

str_re='[[:space:]]*:[[:space:]]*"([^"]*)"'
re_sid="\"session_id\"$str_re"
re_cwd="\"cwd\"$str_re"
re_ask="\"tool_name\"[[:space:]]*:[[:space:]]*\"(AskUserQuestion|ExitPlanMode)\""

sid=""
[[ $input =~ $re_sid ]] && sid="${BASH_REMATCH[1]}"
sid="${sid//[!A-Za-z0-9._-]/}"
[ -z "$sid" ] && sid="default"
f="$dir/$sid.json"

case "$state" in
    end|sleeping)
        rm -f "$f"
        exit 0
        ;;
esac

# 這兩個工具是 Claude 在問你問題／等你核准計畫，實際上需要你介入
[ "$state" = "working" ] && [[ $input =~ $re_ask ]] && state="waiting"

# cwd 在 JSON 裡是跳脫過的字串（Windows 路徑是雙反斜線 \\）。
# 一律轉成正斜線：\\ → // → /，寫回 JSON 時就不必再處理跳脫。
cwd=""
[[ $input =~ $re_cwd ]] && cwd="${BASH_REMATCH[1]}"
cwd="${cwd//\\//}"
cwd="${cwd//\/\//\/}"
[[ $cwd == ?*/ ]] && cwd="${cwd%/}"
project="${cwd##*/}"
[ -z "$project" ] && project="$cwd"
[ -z "$project" ] && project="$sid"

# 沿用既有檔案的 start（首次出現時間），同狀態則沿用 since
start="$now"
since="$now"
if [ -f "$f" ]; then
    old=""
    IFS= read -r -d '' old < "$f"
    if [[ $old =~ \"ts\":([0-9.]+) ]]; then
        to_us "${BASH_REMATCH[1]}"; old_us="$REPLY"
        to_us "$now"; now_us="$REPLY"
        # 比現有狀態舊的事件（async 亂序）直接放棄
        (( now_us < old_us )) && exit 0
    fi
    [[ $old =~ \"start\":([0-9.]+) ]] && start="${BASH_REMATCH[1]}"
    [[ $old =~ \"state\":\"([a-z]+)\" ]] && [ "${BASH_REMATCH[1]}" = "$state" ] &&
        [[ $old =~ \"since\":([0-9.]+) ]] && since="${BASH_REMATCH[1]}"
fi

# 原子寫入（tmp 檔名帶 PID，避免同 session 的兩個 hook 互踩 tmp 檔）
tmp="$dir/.$sid.$$.tmp"
printf '{"state":"%s","ts":%s,"since":%s,"start":%s,"sid":"%s","project":"%s","cwd":"%s"}' \
    "$state" "$now" "$since" "$start" "$sid" "$project" "$cwd" > "$tmp"
mv -f "$tmp" "$f"
