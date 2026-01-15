#!/bin/bash

# Simple test script to verify the server compiles and runs

echo "Testing Email Watchlist Server..."

# Check if cargo is available
if ! command -v cargo &> /dev/null; then
    echo "Error: Rust/cargo not found. Please install Rust first."
    exit 1
fi

# Try to build the project
echo "Building the project..."
cargo build --release 2>&1 | head -20

if [ $? -eq 0 ]; then
    echo "✓ Build successful!"
    
    # Check if the binary exists
    if [ -f "target/release/email_watchlist_server" ]; then
        echo "✓ Binary created successfully"
        echo ""
        echo "To run the server:"
        echo "  cargo run --release"
        echo ""
        echo "The server will start on 0.0.0.0:8080"
        echo "API endpoint: POST /api/watchlist"
    else
        echo "✗ Binary not found after build"
    fi
else
    echo "✗ Build failed"
fi

echo ""
echo "Files created:"
ls -la | grep -E "(Cargo\.toml|src|watchlist|README)"

echo ""
echo "Next steps:"
echo "1. Replace the placeholder GPG public key in watchlist_form.html and watchlist_widget.js"
echo "2. Update the API endpoint if needed"
echo "3. Deploy the server to your hosting"
echo "4. Embed the widget in your landing pages"