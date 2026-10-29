#!/bin/sh
# Deploy reports/worker.js as the Worker oneos-reports, from the team's server.
#
#   reports/deploy.sh            first time and after any change to worker.js
#
# Needs a Cloudflare API token in ~/.oneos-cloudflare (mode 600; Workers Scripts
# Edit, Workers KV Storage Edit, Account Settings Read). Creates on first use,
# and keeps in mode-600 files in the home folder:
#   ~/.oneos-reports-upload-key   the key the app sends (it can only add reports)
#   ~/.oneos-reports-admin-key    the key reports/pull.py reads with
#   ~/.oneos-reports-url          the Worker's address (app/build.gradle.kts reads it)
# The KV namespace "oneos-reports" is found by name or created. The secrets go
# to wrangler on stdin: no key or token is printed or put on a command line.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WRANGLER=${WRANGLER:-"npx --yes wrangler@4.150.0"}
TOKEN_FILE=$HOME/.oneos-cloudflare
[ -s "$TOKEN_FILE" ] || { echo "No Cloudflare token in $TOKEN_FILE"; exit 1; }
CLOUDFLARE_API_TOKEN=$(cat "$TOKEN_FILE")
export CLOUDFLARE_API_TOKEN

umask 077
for k in upload admin; do
    f=$HOME/.oneos-reports-$k-key
    [ -s "$f" ] || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$f"
done

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cp "$HERE/worker.js" "$HERE/wrangler.toml" "$WORK/"
cd "$WORK"

# The namespace, by title.
ID=$($WRANGLER kv namespace list 2>/dev/null | python3 -c 'import json,sys
for n in json.load(sys.stdin):
    if n["title"] == "oneos-reports": print(n["id"])')
if [ -z "$ID" ]; then
    $WRANGLER kv namespace create oneos-reports >/dev/null
    ID=$($WRANGLER kv namespace list 2>/dev/null | python3 -c 'import json,sys
for n in json.load(sys.stdin):
    if n["title"] == "oneos-reports": print(n["id"])')
fi
[ -n "$ID" ] || { echo "Could not find or create the KV namespace oneos-reports"; exit 1; }
sed -i "s/KV_NAMESPACE_ID/$ID/" wrangler.toml
echo "KV namespace oneos-reports: $ID"

$WRANGLER deploy 2>&1 | tee deploy.log | grep -E "Uploaded|Deployed|https://|error|Error" || true
URL=$(grep -o 'https://oneos-reports\.[a-z0-9-]*\.workers\.dev' deploy.log | head -1)
[ -n "$URL" ] || { echo "No workers.dev address in the deploy output"; exit 1; }
printf '%s\n' "$URL" > "$HOME/.oneos-reports-url"

secret() { # <name> <value on stdin>
    $WRANGLER secret put "$1" >/dev/null 2>&1 && echo "secret $1 set" || { echo "secret $1 FAILED"; exit 1; }
}
secret UPLOAD_KEY < "$HOME/.oneos-reports-upload-key"
secret ADMIN_KEY < "$HOME/.oneos-reports-admin-key"
if [ -s "$HOME/.oneos-tg-bot" ] && [ -s "$HOME/.oneos-tg-group" ]; then
    secret TG_TOKEN < "$HOME/.oneos-tg-bot"
    sed -n 's/^chat_id=//p' "$HOME/.oneos-tg-group" | tr -d '\n' | secret TG_CHAT
    sed -n 's/^reports_thread=//p' "$HOME/.oneos-tg-group" | tr -d '\n' | secret TG_THREAD
fi
echo "Deployed: $URL"
