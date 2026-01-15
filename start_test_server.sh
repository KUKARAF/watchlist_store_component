#!/bin/bash

# Start the test server with authentication enabled
export AUTH_USERNAME="testuser"
export AUTH_PASSWORD="testpass"
export DATABASE="watchlist.db"
export PLAIN_DATABASE="watchlist_plain.db"
export GPG_KEY_ID="0x633B15F3E78FCD9A251D53974AFCB3FEAE441839"
export API_ENDPOINT="https://watchlist.layer55.eu/api/watchlist"
export PORT="8080"
export HOST="0.0.0.0"

echo "🚀 Starting test server with Basic Auth enabled..."
echo "Username: $AUTH_USERNAME"
echo "Password: $AUTH_PASSWORD"
echo "Port: $PORT"
echo ""

# Start the server
python3 app.py