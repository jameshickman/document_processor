import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET } from "../lib/API.js";
import {html, css} from "lit";


class ApiConfig extends BaseComponent {
    static styles = css`
        .api-credentials {
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .credentials-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .credentials-table th,
        .credentials-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        .credentials-table th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        
        .credential-value {
            font-family: 'Courier New', monospace;
            background-color: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            word-break: break-all;
            position: relative;
        }
        
        .secret-hidden {
            filter: blur(4px);
            user-select: none;
        }
        
        .toggle-visibility {
            background: #007bff;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }
        
        .toggle-visibility:hover {
            background: #0056b3;
        }
        
        .copy-button {
            background: #28a745;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 5px;
        }
        
        .copy-button:hover {
            background: #1e7e34;
        }
        
        .generate-button {
            background: #dc3545;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin: 20px 0;
        }
        
        .generate-button:hover {
            background: #c82333;
        }
        
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .status-message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            display: none;
        }
        
        .status-message.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-message.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .warning-text {
            color: #856404;
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 14px;
        }
    `;

    static properties = {
        apiKey: { type: String },
        apiSecret: { type: String },
        secretVisible: { type: Boolean },
        loading: { type: Boolean },
        statusMessage: { type: String },
        statusType: { type: String }
    };

    constructor() {
        super();
        this.apiKey = '';
        this.apiSecret = '';
        this.secretVisible = false;
        this.loading = false;
        this.statusMessage = '';
        this.statusType = '';
    }

    connectedCallback() {
        super.connectedCallback();
    }

    server_interface(api) {
        this.init_server(api);
        this.server.define_endpoint(
            "/api_config/key",
            (resp) => {
                this.handleApiCredentialsResponse(resp);
            },
            HTTP_GET
        );

        this.server.define_endpoint(
            "/api_config/generate",
            (resp) => {
                this.handleGenerateResponse(resp);
                // Reload credentials after generation
                setTimeout(() => this.loadApiCredentials(), 500);
            },
            HTTP_GET
        );
    }

    login_success() {
        // Called when user successfully logs in
        // Fetch the API credentials information
        this.loadApiCredentials();
    }

    handleApiCredentialsResponse(resp) {
        this.loading = false;
        if (resp && resp.api_key && resp.api_secret) {
            this.apiKey = resp.api_key;
            this.apiSecret = resp.api_secret;
            this.showStatus('Credentials loaded successfully', 'success');
        } else {
            this.showStatus('Failed to load credentials', 'error');
        }
        this.requestUpdate();
    }

    handleGenerateResponse(resp) {
        this.loading = false;
        if (resp && resp.api_key && resp.api_secret) {
            this.apiKey = resp.api_key;
            this.apiSecret = resp.api_secret;
            this.showStatus('New credentials generated successfully!', 'success');
        } else {
            this.showStatus('Failed to generate new credentials', 'error');
        }
        this.requestUpdate();
    }

    loadApiCredentials() {
        this.loading = true;
        this.requestUpdate();
        if (this.server) {
            this.server.call("/api_config/key");
        }
    }

    generateNewCredentials() {
        if (confirm('Are you sure you want to generate new API credentials? This will invalidate your current credentials.')) {
            this.loading = true;
            this.requestUpdate();
            if (this.server) {
                this.server.call("/api_config/generate");
            }
        }
    }

    toggleSecretVisibility() {
        this.secretVisible = !this.secretVisible;
        this.requestUpdate();
    }

    async copyToClipboard(text, buttonElement) {
        try {
            await navigator.clipboard.writeText(text);
            const originalText = buttonElement.textContent;
            buttonElement.textContent = 'Copied!';
            setTimeout(() => {
                buttonElement.textContent = originalText;
            }, 2000);
        } catch (err) {
            console.error('Failed to copy: ', err);
        }
    }

    showStatus(message, type) {
        this.statusMessage = message;
        this.statusType = type;
        this.requestUpdate();
        // Hide status after 5 seconds
        setTimeout(() => {
            this.statusMessage = '';
            this.requestUpdate();
        }, 5000);
    }

    render() {
        return html`
            <div class="api-credentials ${this.loading ? 'loading' : ''}">
                <h4>Your API Credentials</h4>
                
                <div class="warning-text">
                    <strong>Important:</strong> Keep your API secret secure. Never share it in public repositories or client-side code.
                </div>

                ${this.statusMessage ? html`
                    <div class="status-message ${this.statusType}" style="display: block;">
                        ${this.statusMessage}
                    </div>
                ` : ''}
                
                <table class="credentials-table">
                    <thead>
                        <tr>
                            <th>Credential</th>
                            <th>Value</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>API Key</strong></td>
                            <td>
                                <div class="credential-value">
                                    ${this.apiKey || 'Loading...'}
                                </div>
                            </td>
                            <td>
                                ${this.apiKey ? html`
                                    <button 
                                        class="copy-button" 
                                        @click=${(e) => this.copyToClipboard(this.apiKey, e.target)}>
                                        Copy
                                    </button>
                                ` : ''}
                            </td>
                        </tr>
                        <tr>
                            <td><strong>API Secret</strong></td>
                            <td>
                                <div class="credential-value ${!this.secretVisible ? 'secret-hidden' : ''}">
                                    ${this.apiSecret || 'Loading...'}
                                </div>
                            </td>
                            <td>
                                ${this.apiSecret ? html`
                                    <button class="toggle-visibility" @click=${this.toggleSecretVisibility}>
                                        ${this.secretVisible ? 'Hide' : 'Show'}
                                    </button>
                                    <button 
                                        class="copy-button" 
                                        @click=${(e) => this.copyToClipboard(this.apiSecret, e.target)}>
                                        Copy
                                    </button>
                                ` : ''}
                            </td>
                        </tr>
                    </tbody>
                </table>
                
                <button 
                    class="generate-button" 
                    @click=${this.generateNewCredentials}
                    ?disabled=${this.loading}>
                    ${this.loading ? 'Generating...' : 'Generate New Credentials'}
                </button>
            </div>
        `;
    }
}

customElements.define('api-config', ApiConfig);