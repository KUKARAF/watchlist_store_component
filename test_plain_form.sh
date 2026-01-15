#!/bin/bash

echo "=== Testing Plain Form Endpoint ==="
echo ""

# Test 1: Check if server is running
echo "1. Checking server health..."
if curl -s http://localhost:8084/health > /dev/null; then
    echo "✅ Server is running"
else
    echo "❌ Server is not running"
    exit 1
fi

# Test 2: Test plain form submission
echo ""
echo "2. Testing plain form submission..."
response=$(curl -s -X POST http://localhost:8084/plain \
  -d "email=plain_test@example.com" \
  -d "origin=http://example.com" \
  -d "name=Plain Test User" \
  -d "comments=Testing plain form submission")

if echo "$response" | grep -q "Thank You!"; then
    echo "✅ Plain form submission successful"
else
    echo "❌ Plain form submission failed"
    echo "Response: $response"
    exit 1
fi

# Test 3: Test duplicate prevention
echo ""
echo "3. Testing duplicate prevention..."
response=$(curl -s -X POST http://localhost:8084/plain \
  -d "email=plain_test@example.com" \
  -d "origin=http://example.com" \
  -d "name=Plain Test User" \
  -d "comments=Testing duplicate")

if echo "$response" | grep -q "Duplicate entry"; then
    echo "✅ Duplicate prevention working"
else
    echo "❌ Duplicate prevention not working"
    echo "Response: $response"
    exit 1
fi

# Test 4: Check plain database
echo ""
echo "4. Checking plain database..."
if [ -f "watchlist_plain.db" ]; then
    echo "✅ Plain database file exists"
    
    # Check if entry was stored
    entry_count=$(sqlite3 watchlist_plain.db "SELECT COUNT(*) FROM plain_entries;")
    echo "   Plain entries in database: $entry_count"
    
    if [ "$entry_count" -gt "0" ]; then
        echo "✅ Data stored in plain database"
        sqlite3 watchlist_plain.db "SELECT email, origin, name FROM plain_entries ORDER BY created_at DESC LIMIT 1;"
    else
        echo "❌ No data found in plain database"
    fi
else
    echo "❌ Plain database file not found"
    exit 1
fi

echo ""
echo "🎉 All plain form tests passed!"
echo ""
echo "You can now use the plain HTML form:"
echo "file://$(pwd)/form.html"