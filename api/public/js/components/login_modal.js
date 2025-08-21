import {BaseComponent} from '../lib/component_base.js';
import {HTTP_POST_FORM} from '../lib/API.js';
import {multicall} from '../lib/jsum.js';
import {css, html} from "lit";

/*
 * Login Modal Component with Google OAuth2 support
 * Uses end-points defined in api/routes/auth.py
 */

export class LoginModal extends BaseComponent {
    static properties = {
        show: {type: Boolean},
        show_error: {type: Boolean},
        username: {type: String, state: true},
        password: {type: String, state: true},
        google_client_id: {type: String, state: true}
    };

    // Templating
    static styles = css`
        #modal {
            justify-content: center;
            align-items: center;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
            font-family: Arial, sans-serif;
        }
        #modal.show {
            display: flex;
        }
        #modal.hide {
            display: none;
        }
        .modal-window {
            background-color: #ffffff;
            margin: auto;
            padding: 30px;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            max-width: 400px;
            min-width: 300px;
            position: relative;
        }
        .modal-header {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
            text-align: center;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .modal-body {
            margin-top: 15px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
            color: #666;
            font-weight: bold;
        }
        input[type="text"], input[type="password"] {
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }
        .btn {
            padding: 10px 20px;
            border: 1px solid #ccc;
            background: #fff;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.3s ease;
            margin-top: 10px;
        }
        .btn:hover {
            background: #f0f0f0;
        }
        .btn-primary {
            background: #007bff;
            color: white;
            border-color: #007bff;
            font-weight: bold;
        }
        .btn-primary:hover {
            background: #0056b3;
            border-color: #0056b3;
        }
        #error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .google-signin-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 12px 20px;
            border: 1px solid #dadce0;
            border-radius: 4px;
            background: white;
            color: #3c4043;
            font-family: 'Roboto', Arial, sans-serif;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
            margin-bottom: 15px;
            text-decoration: none;
        }
        .google-signin-btn:hover {
            background: #f8f9fa;
            border-color: #dadce0;
            box-shadow: 0 1px 2px 0 rgba(60, 64, 67, 0.30), 0 1px 3px 1px rgba(60, 64, 67, 0.15);
        }
        .google-signin-btn:active {
            background: #f1f3f4;
        }
        .google-logo {
            width: 18px;
            height: 18px;
            margin-right: 12px;
        }
        .divider {
            display: flex;
            align-items: center;
            margin: 20px 0;
            color: #666;
            font-size: 12px;
        }
        .divider::before,
        .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #ddd;
        }
        .divider::before {
            margin-right: 16px;
        }
        .divider::after {
            margin-left: 16px;
        }
    `;

    constructor() {
        super();
        this.show = true;
        this.show_error = false;
        this.username = '';
        this.password = '';
        this.google_client_id = '';
    }

    login_success(resp) {
        this.username = '';
        this.password = '';
        this.show = false;
        this.dispatchEvent(new CustomEvent('login', {detail: {username: this.username}}));
        this.requestUpdate();
    }

    async fetchGoogleClientId() {
        try {
            const response = await fetch('/auth/google_client_id');
            const data = await response.json();
            this.google_client_id = data.client_id;
            this.requestUpdate();
        } catch (error) {
            console.error('Failed to fetch Google Client ID:', error);
        }
    }

    handleGoogleLogin() {
        if (!this.google_client_id) {
            console.error('Google Client ID not available');
            return;
        }

        const params = new URLSearchParams({
            client_id: this.google_client_id,
            redirect_uri: window.location.origin + '/auth/google/callback',
            scope: 'openid email profile',
            response_type: 'code',
            access_type: 'offline',
            prompt: 'consent'
        });

        const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
        window.location.href = googleAuthUrl;
    }

    // JSUM listeners
    server_interface(api) {
        this.init_server(api);
        this.fetchGoogleClientId();
        
        this.server.define_endpoint(
            "/auth/login",
            (response) => {
                if (response.success) {
                    this.server.set_bearer_token(response.jwt);
                    multicall(
                        {
                            "target": "login_success",
                            "query": "[jsum]",
                            "params": [response]
                        }
                    ).then((results) => {
                        // For now, just log the results
                        // console.log(results);
                    })
                }
                else {
                    this.show_error = true;
                }
            },
            HTTP_POST_FORM
        );
    }

    // Event handlers
    _onUsernameInput(e) {
        this.username = e.target.value;
    }

    _onPasswordInput(e) {
        this.password = e.target.value;
    }

    async handle_submit(e) {
        e.preventDefault();
        this.show_error = false;
        this.server.call(
            "/auth/login",
            HTTP_POST_FORM,
            {
                username: this.username,
                password: this.password
            }
        )
        return false;
    }

    render() {
        return html`
            <div id="modal" class="login-listen ${this.show ? 'show' : 'hide'}">
                <div class="modal-window">
                    <div class="modal-header">Log-in</div>
                    <p id="error" ?hidden=${!this.show_error}>Invalid username or password</p>
                    <div class="modal-body">
                        ${this.google_client_id ? html`
                            <button class="google-signin-btn" @click=${this.handleGoogleLogin}>
                                <svg class="google-logo" viewBox="0 0 24 24">
                                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                </svg>
                                Sign in with Google
                            </button>
                            <div class="divider">or</div>
                        ` : ''}
                        
                        <form id="login-form" class="form">
                            <div class="form-group">
                                <label for="username">Username</label>
                                <input type="text" id="username" name="username" .value=${this.username} @input=${this._onUsernameInput} required />
                                <label for="password">Password</label>
                                <input type="password" id="password" name="password" .value=${this.password} @input=${this._onPasswordInput} required />
                                <button type="submit" class="btn btn-primary" @click=${this.handle_submit}>Log-in</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }
}

customElements.define('login-modal', LoginModal);