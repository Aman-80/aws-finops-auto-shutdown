#!/bin/bash
# Developer override request — simulates Slack /keepup command (M6 mein actual Slack)
# Usage: ./scripts/request_override.sh <instance-id> [hours]

set -e

INSTANCE_ID=${1:?"Usage: $0 <instance-id> [hours]"}
HOURS=${2:-4}

EXPIRES_AT=$(($(date +%s) + HOURS * 3600))
REQUESTED_BY=$(whoami)

aws dynamodb put-item \
  --table-name finops-shutdown-overrides \
  --item "{
    \"instance_id\": {\"S\": \"$INSTANCE_ID\"},
    \"requested_by\": {\"S\": \"$REQUESTED_BY\"},
    \"expires_at\": {\"N\": \"$EXPIRES_AT\"},
    \"reason\": {\"S\": \"manual override via CLI\"}
  }" >/dev/null

echo "✅ Override created"
echo "   Instance:    $INSTANCE_ID"
echo "   Duration:    $HOURS hour(s)"
echo "   Expires at:  $(date -d @$EXPIRES_AT)"
echo "   Requested by: $REQUESTED_BY"
