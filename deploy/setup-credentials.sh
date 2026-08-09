#!/usr/bin/env bash
#
# Place the credentials each lane needs, in the files the connectors actually read.
#
# Secrets are typed at a prompt with echo off. They are never taken as arguments, because
# an argument is visible in `ps` to every user on the box and lands in ~/.bash_history,
# where it outlives any amount of care taken afterwards. `echo "key" > file` has the same
# problem and is the usual way this goes wrong.
#
# Nothing here is written into the repository. The connectors read from the home
# directory precisely so that a public checkout can never contain a key.
set -euo pipefail

umask 077   # anything created below is 600 from birth, not chmod'd afterwards

# Read from the terminal when there is one, so that a stray pipe cannot feed a secret in
# by accident. Fall back to stdin when there is not, so the script still works over a
# non-interactive ssh and can be exercised by a test.
# Testing with `[ -r /dev/tty ]` is not enough: the node can exist and still fail to
# open when the process has no controlling terminal. Try the open itself.
INPUT=/dev/stdin
if { exec 3</dev/tty; } 2>/dev/null; then INPUT=/dev/fd/3; fi

ask() {  # ask <prompt> -> echoes the secret on stdout, never to the terminal
    local prompt="$1" value=""
    read -rsp "  ${prompt}: " value <"$INPUT"
    printf '\n' >&2
    printf '%s' "$value"
}

place() {  # place <directory> <filename> <prompt>
    local dir="$1" name="$2" prompt="$3" value
    value="$(ask "$prompt")"
    if [ -z "$value" ]; then
        printf '  skipped %s/%s (nothing entered)\n\n' "$dir" "$name" >&2
        return
    fi
    mkdir -p "$dir"
    chmod 700 "$dir"
    printf '%s\n' "$value" > "$dir/$name"
    chmod 600 "$dir/$name"
    printf '  wrote %s/%s (%s)\n\n' "$dir" "$name" "$(stat -c '%a' "$dir/$name")" >&2
}

printf '\nCredentials are optional one at a time. Press ENTER to skip any of them;\n'
printf 'preflight will tell you what is still missing and what each one unlocks.\n\n'

printf 'THE ODDS API  (free key at the-odds-api.com) -> ~/.oddsapi/key\n'
place "$HOME/.oddsapi" key "Odds API key"

printf 'ALPACA  -> ~/.alpaca/{key_id,secret_key}\n'
place "$HOME/.alpaca" key_id "Alpaca key id"
place "$HOME/.alpaca" secret_key "Alpaca secret key"

# The marker is a separate, deliberate act. A key gives no hint which environment it
# belongs to and the base URLs differ by one word, so the connector refuses to load
# unless EXACTLY ONE of these exists. A live order placed believing it was paper is not
# a bug you find later.
if [ -f "$HOME/.alpaca/key_id" ]; then
    printf 'Which Alpaca environment do these belong to?\n'
    printf '  [p] paper (recommended: start here)\n  [l] live  (real money)\n'
    read -rp "  p/l: " which <"$INPUT"
    rm -f "$HOME/.alpaca/paper" "$HOME/.alpaca/live"
    case "$which" in
        l|L)
            read -rp "  Type LIVE to confirm real money: " confirm <"$INPUT"
            if [ "$confirm" = "LIVE" ]; then
                touch "$HOME/.alpaca/live"; printf '  marked LIVE\n\n'
            else
                touch "$HOME/.alpaca/paper"; printf '  not confirmed — marked paper\n\n'
            fi ;;
        *) touch "$HOME/.alpaca/paper"; printf '  marked paper\n\n' ;;
    esac
    chmod 600 "$HOME"/.alpaca/paper "$HOME"/.alpaca/live 2>/dev/null || true
fi

# Not a lane. It is how a lane reaches you, and one that finds something at 16:00 on a
# Monday and tells nobody has not done its job. Absent, everything still runs and the
# notifier reports NOT_CONFIGURED, which is not a failure.
printf 'TELEGRAM  (notifications) -> ~/.telegram/{bot_token,chat_id}\n'
printf '  token from @BotFather, your chat id from @userinfobot\n'
place "$HOME/.telegram" bot_token "Telegram bot token"
place "$HOME/.telegram" chat_id "Telegram chat id (not secret; hidden anyway)"

printf 'What is in place now:\n\n'
find "$HOME/.oddsapi" "$HOME/.alpaca" "$HOME/.telegram" "$HOME/.betfair" "$HOME/.smarkets" \
     -type f -printf '  %m  %p\n' 2>/dev/null || true
printf '\nAnything not 600 above is readable by another user. Now run:\n'
printf '  python preflight.py\n\n'
