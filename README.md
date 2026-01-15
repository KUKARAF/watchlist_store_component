# Email Watchlist Service - Python/Flask Version

A simple Python/Flask web service for collecting email watchlist signups with GPG encryption.

## Features

- **Simple Python/Flask backend** - Easy to understand and modify
- **GPG key fetching** - Automatically fetches public keys from keys.openpgp.org
- **SQLite database** - Simple file-based storage
- **Client-side encryption** - JavaScript widget with OpenPGP.js
- **Easy embedding** - Widget for any landing page

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
python app.py
```

Or with environment variables:

```bash
GPG_KEY_ID=0xYOUR_KEY_ID API_ENDPOINT=https://watchlist.layer55.eu/api/watchlist python app.py
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8080/health

# Get GPG key
curl http://localhost:8080/gpg-key

# Submit test data
curl -X POST http://localhost:8080/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","origin":"https://example.com","encrypted_data":"test"}'
```

## Docker Deployment

### 1. Build and run

```bash
docker compose up -d --build
```

### 2. Configuration

Edit `docker-compose.yaml`:

```yaml
environment:
  - GPG_KEY_ID=0xYOUR_KEY_ID  # Your GPG key ID from keys.openpgp.org
  - API_ENDPOINT=https://watchlist.layer55.eu/api/watchlist
```

## JavaScript Widget

### Basic Embedding

```html
<script src="https://watchlist.layer55.eu/watchlist_widget.js"></script>
<div id="watchlist-form-container"></div>
```

### Custom Configuration

```html
<script>
  window.WatchlistConfig = {
    formTitle: 'Join Our Waitlist',
    formDescription: 'Sign up for early access!',
    submitButtonText: 'Join Now'
  };
</script>
<script src="https://watchlist.layer55.eu/watchlist_widget.js"></script>
<div id="watchlist-form-container"></div>
```

## API Endpoints

### GET `/health`
Health check endpoint

**Response:**
```json
{"status": "healthy"}
```

### GET `/gpg-key`
Returns the public GPG key for client-side encryption

**Response:**
```
-----BEGIN PGP PUBLIC KEY BLOCK-----
...
-----END PGP PUBLIC KEY BLOCK-----
```

### POST `/api/watchlist`
Submit watchlist signup

**Request Body:**
```json
{
  "email": "user@example.com",
  "origin": "https://landing.page.com",
  "name": "John Doe",
  "comments": "Interested in beta",
  "encrypted_data": "-----BEGIN PGP MESSAGE-----..."
}
```

**Response (Success):**
```json
{"message": "Thank you for joining our waitlist!"}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GPG_KEY_ID` | Your GPG key ID or email | `0x633B15F3E78FCD9A251D53974AFCB3FEAE441839` |
| `API_ENDPOINT` | Public API endpoint | `https://watchlist.layer55.eu/api/watchlist` |
| `PORT` | Server port | `8080` |

### GPG Key Setup

1. Upload your public key to [keys.openpgp.org](https://keys.openpgp.org/)
2. Get your key ID: `gpg --list-keys` or `gpg --fingerprint your@email.com`
3. Set the `GPG_KEY_ID` environment variable

## Database

The service uses SQLite and creates `watchlist.db` automatically.

**Schema:**
```sql
CREATE TABLE watchlist_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    origin TEXT NOT NULL,
    name TEXT,
    comments TEXT,
    encrypted_data TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

## Security

- All sensitive data is encrypted with GPG before transmission
- GPG keys are fetched dynamically from keys.openpgp.org
- Only email sent unencrypted (for basic validation)
- Use HTTPS in production

## Deployment

### Production with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### With Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name watchlist.layer55.eu;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Troubleshooting

### GPG Key Not Found

```bash
# Test key fetching manually
curl https://keys.openpgp.org/vks/v1/by-keyid/0xYOUR_KEY_ID

# Upload your key if needed
gpg --export --armor YOUR_KEY_ID > my-key.asc
curl -T my-key.asc https://keys.openpgp.org/upload
```

### Database Issues

```bash
# Check database
sqlite3 watchlist.db "SELECT * FROM watchlist_entries LIMIT 5;"

# Reset database (careful!)
rm watchlist.db
```

## License

MIT License