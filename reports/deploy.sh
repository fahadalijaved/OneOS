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
#   ~/.oneos-reports-pass-key     0.5.16: signs the Telegram pass (reports from group members only)
#   ~/.oneos-reports-hook-key     0.5.16: the bot webhook's secret token
# and reads ~/.oneos-signin-bot, the sign-in bot's token (@OneOSReportsBot);
# without it the ping bot (~/.oneos-tg-bot) signs people in.
# and reads ~/.oneos-reports-require-member: "1" refuses apps without a pass
# (0.5.15 and older); absent or anything else still takes them.
# Keep these files the same on every account that deploys (a new pass key signs
# everyone out; a new upload key stops every installed app sending).
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
for k in upload admin pass hook; do
    f=$HOME/.oneos-reports-$k-key
    [ -s "$f" ] || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$f"
done

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cp "$HERE/worker.js" "$HERE/store.js" "$HERE/package.json" "$HERE/wrangler.toml" "$WORK/"
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

# 0.5.18: the D1 database "oneos-reports" (store.js; KV's 1000 writes a day ran out), by name or created, and its
# tables (CREATE ... IF NOT EXISTS: nothing in them is touched on a later deploy).
d1id() { $WRANGLER d1 list --json 2>/dev/null | python3 -c 'import json,sys
for d in json.load(sys.stdin):
    if d.get("name") == "oneos-reports": print(d.get("uuid") or d.get("database_id") or "")'; }
DB=$(d1id)
if [ -z "$DB" ]; then
    $WRANGLER d1 create oneos-reports >/dev/null
    DB=$(d1id)
fi
[ -n "$DB" ] || { echo "Could not find or create the D1 database oneos-reports"; exit 1; }
sed -i "s/D1_DATABASE_ID/$DB/" wrangler.toml
node -e 'import("./store.js").then((m) => process.stdout.write(m.SCHEMA.join(";\n") + ";\n"))' > schema.sql
$WRANGLER d1 execute oneos-reports --remote --yes --file schema.sql >/dev/null 2>&1 || { echo "D1 schema FAILED"; exit 1; }
echo "D1 database oneos-reports: $DB (tables ready)"

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
    # 0.5.16: sign-in through the bot. Its username (public), the pass key, the
    # webhook's secret, and the webhook itself (only "message" updates).
    secret PASS_KEY < "$HOME/.oneos-reports-pass-key"
    secret TG_HOOK < "$HOME/.oneos-reports-hook-key"
    # The sign-in bot: its own token in ~/.oneos-signin-bot (@OneOSReportsBot), else the ping bot.
    SIGNIN=$HOME/.oneos-signin-bot; [ -s "$SIGNIN" ] || SIGNIN=$HOME/.oneos-tg-bot
    secret TG_SIGNIN_TOKEN < "$SIGNIN"
    python3 -I - "$SIGNIN" <<'EOF' | tr -d '\n' | secret TG_BOT
import json, sys, urllib.request
tok = open(sys.argv[1]).read().strip()
print(json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getMe", timeout=20))["result"]["username"])
EOF
    req=0; [ "$(cat "$HOME/.oneos-reports-require-member" 2>/dev/null)" = 1 ] && req=1
    printf %s "$req" | secret REQUIRE_MEMBER
    python3 -I - "$SIGNIN" "$HOME/.oneos-reports-hook-key" "$URL/v1/tg" <<'EOF'
import json, sys, urllib.request
tok, hook = (open(f).read().strip() for f in sys.argv[1:3])
body = json.dumps({"url": sys.argv[3], "secret_token": hook, "allowed_updates": ["message"]}).encode()
r = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/setWebhook", data=body,
    headers={"Content-Type": "application/json"}), timeout=20))
print("bot webhook:", "set" if r.get("ok") else "FAILED " + str(r.get("description")))
EOF
fi
echo "Deployed: $URL"
