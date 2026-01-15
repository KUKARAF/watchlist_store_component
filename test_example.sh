#!/bin/bash

echo "Testing the example HTML page..."
echo "Server should be running on http://localhost:8084"
echo ""

# Check if server is running
if curl -s http://localhost:8084/health > /dev/null; then
    echo "✅ Server is running and healthy"
else
    echo "❌ Server is not running on localhost:8084"
    exit 1
fi

# Test GPG key endpoint
if curl -s http://localhost:8084/gpg-key | grep -q "BEGIN PGP PUBLIC KEY BLOCK"; then
    echo "✅ GPG key endpoint working"
else
    echo "❌ GPG key endpoint not working"
    exit 1
fi

# Test API endpoint
echo "Testing API endpoint..."
response=$(curl -s -X POST http://localhost:8084/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"email":"test2@example.com","origin":"http://localhost:8084/example","name":"Example User","comments":"Testing from example page","encrypted_data":"encrypted data for testing the example page functionality"}')

if echo "$response" | grep -q "Thank you for joining our waitlist"; then
    echo "✅ API endpoint working"
else
    echo "❌ API endpoint failed: $response"
    exit 1
fi

echo ""
echo "🎉 All tests passed!"
echo ""
echo "You can now open the example page:"
echo "file://$(pwd)/example/index.html"
echo ""
echo "Or use the test submission page:"
echo "file://$(pwd)/test_submission.html"