/**
 * Email Watchlist Widget
 * Embed this script in any landing page to add a watchlist signup form
 * 
 * Usage:
 * <script src="https://watchlist.layer55.eu/watchlist_widget.js"></script>
 * <div id="watchlist-form-container"></div>
 * 
 * Or with custom GPG key:
 * <script>
 *   window.WatchlistConfig = {
 *     gpgPublicKey: 'YOUR_GPG_PUBLIC_KEY_HERE'
 *   };
 * </script>
 * <script src="https://watchlist.layer55.eu/watchlist_widget.js"></script>
 * <div id="watchlist-form-container"></div>
 */

(function() {
    // Default configuration
    const DEFAULT_CONFIG = {
        gpgPublicKey: `-----BEGIN PGP PUBLIC KEY BLOCK-----
        
        mQENBF3ABCDBCADABCD1234567890ABCDEF1234567890ABCDEF12345678
        90ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12
        34567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890AB
        CDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF123456
        7890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF
        1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890
        ABCD
        =ABCD
        -----END PGP PUBLIC KEY BLOCK-----`,
        apiEndpoint: 'https://watchlist.layer55.eu/api/watchlist',
        formTitle: 'Join Our Waitlist',
        formDescription: 'Sign up to get early access to our product!',
        submitButtonText: 'Join Waitlist'
    };

    // Merge with user configuration
    const config = { ...DEFAULT_CONFIG, ...window.WatchlistConfig };

    // Load OpenPGP.js
    function loadOpenPGP() {
        return new Promise((resolve, reject) => {
            if (window.openpgp) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/openpgp@5.0.0/dist/openpgp.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // Create the form HTML
    function createFormHTML() {
        return `
        <div class="watchlist-form">
            <h3>${config.formTitle}</h3>
            <p>${config.formDescription}</p>
            
            <form id="watchlistForm">
                <div class="form-group">
                    <label for="watchlistEmail">Email Address *</label>
                    <input type="email" id="watchlistEmail" name="email" required>
                </div>
                
                <div class="form-group">
                    <label for="watchlistName">Your Name</label>
                    <input type="text" id="watchlistName" name="name">
                </div>
                
                <div class="form-group">
                    <label for="watchlistComments">Additional Comments</label>
                    <textarea id="watchlistComments" name="comments"></textarea>
                </div>
                
                <button type="submit" id="watchlistSubmitBtn">
                    <span id="buttonText">${config.submitButtonText}</span>
                    <span id="loadingSpinner" class="loading" style="display: none;"></span>
                </button>
            </form>
            
            <div id="successMessage" class="success-message" style="display: none;">
                Thank you for joining our waitlist!
            </div>
            
            <div id="errorMessage" class="error-message" style="display: none;">
                Error submitting your request. Please try again.
            </div>
            
            <style>
                .watchlist-form {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                    border: 1px solid #eee;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .watchlist-form .form-group {
                    margin-bottom: 15px;
                }
                .watchlist-form label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                }
                .watchlist-form input[type="email"],
                .watchlist-form input[type="text"],
                .watchlist-form textarea {
                    width: 100%;
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                .watchlist-form textarea {
                    height: 100px;
                }
                .watchlist-form button {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                }
                .watchlist-form button:hover {
                    background-color: #45a049;
                }
                .watchlist-form .success-message {
                    color: green;
                    margin-top: 20px;
                    font-weight: bold;
                }
                .watchlist-form .error-message {
                    color: red;
                    margin-top: 20px;
                    font-weight: bold;
                }
                .watchlist-form .loading {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(0,0,0,.3);
                    border-radius: 50%;
                    border-top-color: #000;
                    animation: spin 1s ease-in-out infinite;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
        </div>
        `;
    }

    // Encrypt data using OpenPGP
    async function encryptData(data) {
        try {
            const publicKey = await openpgp.readKey({ armoredKey: config.gpgPublicKey });
            
            const encrypted = await openpgp.encrypt({
                message: await openpgp.createMessage({ text: data }),
                encryptionKeys: publicKey,
                format: 'armored'
            });
            
            return encrypted;
        } catch (error) {
            console.error('Encryption error:', error);
            throw error;
        }
    }

    // Handle form submission
    async function handleSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const button = form.querySelector('#watchlistSubmitBtn');
        const buttonText = form.querySelector('#buttonText');
        const loadingSpinner = form.querySelector('#loadingSpinner');
        const successMessage = form.querySelector('#successMessage');
        const errorMessage = form.querySelector('#errorMessage');
        
        // Show loading state
        buttonText.textContent = 'Processing...';
        loadingSpinner.style.display = 'inline-block';
        button.disabled = true;
        
        // Hide messages
        successMessage.style.display = 'none';
        errorMessage.style.display = 'none';
        
        try {
            const email = form.querySelector('#watchlistEmail').value;
            const name = form.querySelector('#watchlistName').value;
            const comments = form.querySelector('#watchlistComments').value;
            const origin = window.location.href;
            
            const dataToEncrypt = {
                email: email,
                name: name,
                comments: comments,
                origin: origin,
                timestamp: new Date().toISOString()
            };
            
            const encryptedData = await encryptData(JSON.stringify(dataToEncrypt));
            
            const response = await fetch(config.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    origin: origin,
                    name: name || null,
                    comments: comments || null,
                    encrypted_data: encryptedData
                })
            });
            
            if (response.ok) {
                form.style.display = 'none';
                successMessage.style.display = 'block';
            } else {
                throw new Error('Server error');
            }
            
        } catch (error) {
            console.error('Error:', error);
            errorMessage.style.display = 'block';
        } finally {
            buttonText.textContent = config.submitButtonText;
            loadingSpinner.style.display = 'none';
            button.disabled = false;
        }
    }

    // Main initialization
    async function init() {
        try {
            await loadOpenPGP();
            
            // Find container
            const container = document.getElementById('watchlist-form-container');
            if (!container) {
                console.warn('Watchlist container not found');
                return;
            }
            
            // Insert form
            container.innerHTML = createFormHTML();
            
            // Set up event listener
            document.getElementById('watchlistForm').addEventListener('submit', handleSubmit);
            
        } catch (error) {
            console.error('Failed to initialize watchlist form:', error);
        }
    }

    // Start initialization
    init();

})();