#!/usr/bin/env python3

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import sqlite3
import requests
import gnupg
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
logger = logging.getLogger(__name__)

# Add file logging
file_handler = RotatingFileHandler(
    'watchlist.log', 
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
logger.addHandler(file_handler)

app = Flask(__name__)

# Configuration
DATABASE = os.environ.get('DATABASE', 'watchlist.db')
PLAIN_DATABASE = os.environ.get('PLAIN_DATABASE', 'watchlist_plain.db')
GPG_KEY_ID = os.environ.get('GPG_KEY_ID', '0x633B15F3E78FCD9A251D53974AFCB3FEAE441839')
API_ENDPOINT = os.environ.get('API_ENDPOINT', 'https://watchlist.layer55.eu/api/watchlist')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max request size

# Basic Auth configuration for protected endpoints
AUTH_USERNAME = os.environ.get('AUTH_USERNAME')
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD')

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

# Fix for reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Database connection pool
db_connection_pool = []
plain_db_connection_pool = []

def get_db_connection():
    """Get a database connection from pool or create new one"""
    if db_connection_pool:
        return db_connection_pool.pop()
    
    try:
        conn = sqlite3.connect(DATABASE, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')  # Better for concurrent access
        conn.execute('PRAGMA synchronous=NORMAL')  # Balance between safety and speed
        conn.execute('PRAGMA busy_timeout=5000')  # 5 second timeout
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def return_db_connection(conn):
    """Return connection to pool"""
    if len(db_connection_pool) < 10:  # Max pool size
        db_connection_pool.append(conn)

def get_plain_db_connection():
    """Get a plain database connection from pool or create new one"""
    if plain_db_connection_pool:
        return plain_db_connection_pool.pop()
    
    try:
        conn = sqlite3.connect(PLAIN_DATABASE, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')  # Better for concurrent access
        conn.execute('PRAGMA synchronous=NORMAL')  # Balance between safety and speed
        conn.execute('PRAGMA busy_timeout=5000')  # 5 second timeout
        return conn
    except sqlite3.Error as e:
        logger.error(f"Plain database connection error: {e}")
        raise

def return_plain_db_connection(conn):
    """Return plain connection to pool"""
    if len(plain_db_connection_pool) < 10:  # Max pool size
        plain_db_connection_pool.append(conn)

# Initialize database
def init_db():
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Create main table if not exists
        c.execute('''
            CREATE TABLE IF NOT EXISTS watchlist_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                origin TEXT NOT NULL,
                name TEXT,
                comments TEXT,
                encrypted_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Add UNIQUE constraint if not exists
        try:
            c.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_email_origin_unique 
                ON watchlist_entries(email, origin)
            ''')
        except sqlite3.OperationalError:
            # Index already exists or other issue, continue
            pass
        
        # Create indexes for better query performance
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_email ON watchlist_entries(email)')
        except sqlite3.OperationalError:
            pass
        
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_origin ON watchlist_entries(origin)')
        except sqlite3.OperationalError:
            pass
        
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_created ON watchlist_entries(created_at)')
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if conn:
            return_db_connection(conn)

def init_plain_db():
    """Initialize the plain database for non-encrypted submissions"""
    conn = None
    try:
        conn = get_plain_db_connection()
        c = conn.cursor()
        # Create plain table if not exists
        c.execute('''
            CREATE TABLE IF NOT EXISTS plain_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                origin TEXT NOT NULL,
                name TEXT,
                comments TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Add UNIQUE constraint if not exists
        try:
            c.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_plain_email_origin_unique 
                ON plain_entries(email, origin)
            ''')
        except sqlite3.OperationalError:
            # Index already exists or other issue, continue
            pass
        
        # Create indexes for better query performance
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_plain_email ON plain_entries(email)')
        except sqlite3.OperationalError:
            pass
        
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_plain_origin ON plain_entries(origin)')
        except sqlite3.OperationalError:
            pass
        
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_plain_created ON plain_entries(created_at)')
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        logger.info("Plain database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize plain database: {e}")
        raise
    finally:
        if conn:
            return_plain_db_connection(conn)

# GPG key caching
gpg_key_cache = None
last_key_fetch = None

def check_basic_auth():
    """Check Basic Authentication credentials"""
    if not AUTH_USERNAME or not AUTH_PASSWORD:
        logger.warning("Basic Auth not configured - AUTH_USERNAME and AUTH_PASSWORD env vars not set")
        return False
    
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return False
    
    return auth.username == AUTH_USERNAME and auth.password == AUTH_PASSWORD


def fetch_gpg_key(force_refresh=False):
    """Fetch GPG key from keys.openpgp.org with caching"""
    global gpg_key_cache, last_key_fetch
    
    # Use cached key if available and not too old
    if gpg_key_cache and last_key_fetch and not force_refresh:
        age = datetime.now() - last_key_fetch
        if age.total_seconds() < 3600:  # Cache for 1 hour
            return gpg_key_cache
    
    try:
        # Support both key ID and email formats
        if '@' in GPG_KEY_ID:
            url = f"https://keys.openpgp.org/vks/v1/by-email/{GPG_KEY_ID}"
        else:
            url = f"https://keys.openpgp.org/vks/v1/by-keyid/{GPG_KEY_ID}"
        
        logger.info(f"Fetching GPG key from: {url}")
        
        # Use timeout and retry for resilience
        response = requests.get(
            url, 
            headers={'Accept': 'application/pgp-keys'},
            timeout=30
        )
        response.raise_for_status()
        
        key_data = response.text
        if not key_data or key_data.strip() == '':
            raise ValueError("Received empty GPG key data")
        
        # Cache the key
        gpg_key_cache = key_data
        last_key_fetch = datetime.now()
        logger.info("Successfully fetched and cached GPG public key")
        
        return key_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching GPG key: {e}")
        if gpg_key_cache:
            logger.warning("Using cached GPG key due to network error")
            return gpg_key_cache
        raise
    except Exception as e:
        logger.error(f"Failed to fetch GPG key: {e}")
        if gpg_key_cache:
            logger.warning("Using cached GPG key due to error")
            return gpg_key_cache
        raise



def store_in_database(email, origin, name, comments, encrypted_data):
    """Store data in database with error handling"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Try to insert, handle duplicates gracefully
        try:
            c.execute('''
                INSERT INTO watchlist_entries (email, origin, name, comments, encrypted_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, origin, name or '', comments or '', encrypted_data, datetime.now().isoformat()))
        except sqlite3.IntegrityError as e:
            # Check if it's a duplicate entry
            if 'UNIQUE constraint failed' in str(e):
                logger.warning(f"Duplicate entry prevented for {email} from {origin}")
                raise ValueError("Duplicate entry: this email and origin combination already exists")
            else:
                raise
        
        conn.commit()
        logger.info(f"Stored entry for {email} from {origin}")
        
    except sqlite3.IntegrityError:
        logger.warning(f"Duplicate entry attempted for {email} from {origin}")
        raise ValueError("Duplicate entry")
    except Exception as e:
        logger.error(f"Database error storing entry: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_db_connection(conn)

def store_plain_entry(email, origin, name, comments):
    """Store plain (non-encrypted) data in separate database"""
    conn = None
    try:
        conn = get_plain_db_connection()
        c = conn.cursor()
        
        # Try to insert, handle duplicates gracefully
        try:
            c.execute('''
                INSERT INTO plain_entries (email, origin, name, comments, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, origin, name or '', comments or '', datetime.now().isoformat()))
        except sqlite3.IntegrityError as e:
            # Check if it's a duplicate entry
            if 'UNIQUE constraint failed' in str(e):
                logger.warning(f"Duplicate plain entry prevented for {email} from {origin}")
                raise ValueError("Duplicate entry: this email and origin combination already exists")
            else:
                raise
        
        conn.commit()
        logger.info(f"Stored plain entry for {email} from {origin}")
        
    except sqlite3.IntegrityError as e:
        logger.warning(f"Duplicate plain entry attempted for {email} from {origin}")
        if 'UNIQUE constraint failed' in str(e):
            raise ValueError("Duplicate entry: this email and origin combination already exists")
        else:
            raise ValueError(f"Database constraint error: {str(e)}")
    except Exception as e:
        logger.error(f"Plain database error storing entry: {e}")
        if conn:
            conn.rollback()
        raise ValueError(f"Database error: {str(e)}")
    finally:
        if conn:
            return_plain_db_connection(conn)

# Rate limiting (simple in-memory version)
rate_limit_store = {}

def check_rate_limit(ip_address, limit=10, window=60):
    """Simple rate limiting to prevent abuse"""
    now = datetime.now()
    
    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = []
    
    # Clean up old requests
    requests = rate_limit_store[ip_address]
    requests = [t for t in requests if (now - t).total_seconds() < window]
    
    if len(requests) >= limit:
        return False
    
    requests.append(now)
    rate_limit_store[ip_address] = requests
    return True

# Routes with proper error handling
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        return_db_connection(conn)
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "ok",
            "gpg_key": "cached" if gpg_key_cache else "not_cached"
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

@app.route('/gpg-key', methods=['GET'])
def gpg_key():
    """Serve GPG public key"""
    try:
        key_data = fetch_gpg_key()
        return key_data, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        logger.error(f"Failed to serve GPG key: {e}")
        return jsonify({"error": "GPG key not available"}), 503

@app.route('/api/watchlist', methods=['POST'])
def submit_watchlist():
    """Handle watchlist submissions"""
    client_ip = request.remote_addr
    
    # Rate limiting
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return jsonify({"error": "Too many requests"}), 429
    
    try:
        # Validate content type
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
        
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        required_fields = ['email', 'origin', 'encrypted_data']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "error": "Missing required fields",
                "missing": missing_fields
            }), 400
        
        # Validate email format
        email = data['email']
        if '@' not in email or '.' not in email:
            return jsonify({"error": "Invalid email format"}), 400
        
        origin = data['origin']
        name = data.get('name', '')
        comments = data.get('comments', '')
        encrypted_data = data['encrypted_data']
        
        # Validate encrypted data
        if not encrypted_data or len(encrypted_data) < 20:
            return jsonify({"error": "Invalid encrypted data"}), 400
        
        logger.info(f"Received submission from {origin} (IP: {client_ip})")
        
        # Store in database
        store_in_database(email, origin, name, comments, encrypted_data)
        
        return jsonify({
            "message": "Thank you for joining our waitlist!",
            "success": True
        }), 200
        
    except ValueError as e:
        logger.warning(f"Validation error from {client_ip}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Server error processing request from {client_ip}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/watchlist/count', methods=['GET'])
def get_watchlist_count():
    """Get the number of people on the waitlist for a specific origin"""
    
    # Check Basic Authentication
    if not check_basic_auth():
        return jsonify({"error": "Unauthorized - Basic Authentication required"}), 401
    
    # Get origin parameter
    origin = request.args.get('origin')
    
    if not origin:
        return jsonify({"error": "Origin parameter is required"}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Count entries for the specific origin
        c.execute('SELECT COUNT(*) FROM watchlist_entries WHERE origin = ?', (origin,))
        count = c.fetchone()[0]
        
        logger.info(f"Count request for origin '{origin}': {count} entries")
        
        return jsonify({
            "origin": origin,
            "count": count,
            "success": True
        }), 200
        
    except sqlite3.Error as e:
        logger.error(f"Database error counting entries for {origin}: {e}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        logger.error(f"Error counting entries for {origin}: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            return_db_connection(conn)

@app.route('/plain', methods=['POST'])
def submit_plain():
    """Handle plain (non-encrypted) submissions for simple HTML forms"""
    client_ip = request.remote_addr
    
    try:
        # Get form data
        email = request.form.get('email', '').strip()
        origin = request.form.get('origin', '').strip()
        name = request.form.get('name', '').strip()
        comments = request.form.get('comments', '').strip()
        
        # Validate required fields
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        if not origin:
            origin = request.referrer or 'unknown'
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({"error": "Invalid email format"}), 400
        
        # Store in plain database
        store_plain_entry(email, origin, name if name else None, comments if comments else None)
        
        # Return HTML response for form submission
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Thank You!</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .success { color: #27ae60; font-size: 24px; margin-bottom: 20px; }
                .message { font-size: 18px; color: #333; }
            </style>
        </head>
        <body>
            <div class="success">✅ Thank You!</div>
            <div class="message">Your email has been added to our waitlist.</div>
        </body>
        </html>
        ''', 200, {'Content-Type': 'text/html'}
        
    except ValueError as e:
        logger.warning(f"Plain submission validation error from {client_ip}: {e}")
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; font-size: 24px; margin-bottom: 20px; }
                .message { font-size: 18px; color: #333; }
            </style>
        </head>
        <body>
            <div class="error">❌ Error</div>
            <div class="message">{}</div>
        </body>
        </html>
        '''.format(str(e)), 400, {'Content-Type': 'text/html'}
    except Exception as e:
        logger.error(f"Server error processing plain request from {client_ip}: {e}")
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; font-size: 24px; margin-bottom: 20px; }
                .message { font-size: 18px; color: #333; }
            </style>
        </head>
        <body>
            <div class="error">❌ Internal Server Error</div>
            <div class="message">Please try again later.</div>
        </body>
        </html>
        ''', 500, {'Content-Type': 'text/html'}


@app.route('/watchlist_widget.js', methods=['GET'])
def serve_widget():
    """Serve JavaScript widget"""
    try:
        return send_from_directory('static', 'watchlist_widget.js')
    except Exception as e:
        logger.error(f"Failed to serve widget: {e}")
        return jsonify({"error": "Widget not available"}), 404

@app.route('/watchlist_form.html', methods=['GET'])
def serve_form():
    """Serve HTML form"""
    try:
        return send_from_directory('static', 'watchlist_form.html')
    except Exception as e:
        logger.error(f"Failed to serve form: {e}")
        return jsonify({"error": "Form not available"}), 404

@app.route('/static/<path:filename>', methods=['GET'])
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f"Failed to serve static file {filename}: {e}")
        return jsonify({"error": "File not found"}), 404

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Initialize databases
    try:
        init_db()
        init_plain_db()
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        exit(1)
    
    # Start server
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting production server on {host}:{port}")
    logger.info(f"GPG Key ID: {GPG_KEY_ID}")
    logger.info(f"API Endpoint: {API_ENDPOINT}")
    
    # Production server (use gunicorn in production)
    app.run(host=host, port=port, threaded=True)
