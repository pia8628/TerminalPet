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
#   - 純 bash 解析 session_id，不 spawn python，維持低延遲。
#   - 原子寫入（先寫 tmp 再 mv），避免桌寵讀到寫到一半的檔。

state="$1"
[ -z "$state" ] && exit 0

dir="$HOME/.terminalpet/sessions"
mkdir -p "$dir"

# 由 hook 的 stdin JSON 取 session_id；取不到就歸到 default（例如手動測試）
input=$(cat 2>/dev/null)
sid=$(printf '%s' "$input" | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"$/\1/')
sid=$(printf '%s' "$sid" | tr -cd 'A-Za-z0-9._-')
[ -z "$sid" ] && sid="default"

# 原子寫入
tmp="$dir/.$sid.tmp"
printf '{"state":"%s","ts":%s,"sid":"%s"}' "$state" "$EPOCHSECONDS" "$sid" > "$tmp"
mv -f "$tmp" "$dir/$sid.json"
