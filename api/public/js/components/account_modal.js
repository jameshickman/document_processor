import {BaseComponent} from '../lib/component_base.js';
import {HTTP_GET, HTTP_POST_JSON} from '../lib/API.js';
import {multicall} from '../lib/jsum.js';
import {css, html} from "lit";

export class AccountModal extends BaseComponent {
    static properties = {
        show: {type: Boolean},
        userInfo: {type: Object},
        showError: {type: Boolean},
        errorMessage: {type: String},
        showSuccess: {type: Boolean},
        successMessage: {type: String},
        name: {type: String, state: true},
        oldPassword: {type: String, state: true},
        newPassword: {type: String, state: true},
        confirmPassword: {type: String, state: true}
    };

    constructor() {
        super();
        this.show = false;
        this.userInfo = null;
        this.showError = false;
        this.errorMessage = '';
        this.showSuccess = false;
        this.successMessage = '';
        this.name = '';
        this.oldPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
    }

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
            font-family: 'Verdana', 'Arial', 'Droid Sans', 'Lato', sans-serif;
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
            max-width: 500px;
            min-width: 400px;
            position: relative;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            position: absolute;
            right: 15px;
            top: 10px;
            cursor: pointer;
        }
        .close:hover {
            color: #000;
        }
        h2 {
            color: #333;
            margin-top: 0;
            margin-bottom: 20px;
        }
        .form-section {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .form-section:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        .form-section h3 {
            color: #555;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #555;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background-color 0.2s;
        }
        .btn-primary {
            background-color: #007bff;
            color: white;
        }
        .btn-primary:hover {
            background-color: #0056b3;
        }
        .btn-secondary {
            background-color: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background-color: #545b62;
        }
        .alert {
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid transparent;
            border-radius: 4px;
        }
        .alert-error {
            color: #721c24;
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        .alert-success {
            color: #155724;
            background-color: #d4edda;
            border-color: #c3e6cb;
        }
    `;

    render() {
        return html`
            <div id="modal" class="${this.show ? 'show' : 'hide'}">
                <div class="modal-window">
                    <span class="close" @click="${this.hideModal}">&times;</span>
                    <h2>Account Settings</h2>

                    ${this.showError ? html`
                        <div class="alert alert-error">
                            ${this.errorMessage}
                        </div>
                    ` : ''}

                    ${this.showSuccess ? html`
                        <div class="alert alert-success">
                            ${this.successMessage}
                        </div>
                    ` : ''}

                    <form @submit="${this.handleSubmit}">
                        <!-- Name Update Section -->
                        <div class="form-section">
                            <h3>Update Name</h3>
                            <div class="form-group">
                                <label for="name">Name:</label>
                                <input type="text" id="name" .value="${this.name}"
                                       @input="${(e) => this.name = e.target.value}">
                            </div>
                            <div class="button-group">
                                <button type="button" class="btn-primary" @click="${this.updateName}">
                                    Update Name
                                </button>
                            </div>
                        </div>

                        <!-- Password Update Section -->
                        <div class="form-section">
                            <h3>Change Password</h3>
                            <div class="form-group">
                                <label for="oldPassword">Current Password:</label>
                                <input type="password" id="oldPassword" .value="${this.oldPassword}"
                                       @input="${(e) => this.oldPassword = e.target.value}">
                            </div>
                            <div class="form-group">
                                <label for="newPassword">New Password:</label>
                                <input type="password" id="newPassword" .value="${this.newPassword}"
                                       @input="${(e) => this.newPassword = e.target.value}">
                            </div>
                            <div class="form-group">
                                <label for="confirmPassword">Confirm New Password:</label>
                                <input type="password" id="confirmPassword" .value="${this.confirmPassword}"
                                       @input="${(e) => this.confirmPassword = e.target.value}">
                            </div>
                            <div class="button-group">
                                <button type="button" class="btn-primary" @click="${this.updatePassword}">
                                    Change Password
                                </button>
                            </div>
                        </div>

                        <!-- Close Button -->
                        <div class="button-group" style="margin-top: 30px; justify-content: center;">
                            <button type="button" class="btn-secondary" @click="${this.hideModal}">
                                Close
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    server_interface(api) {
        this.init_server(api);

        // Get account info endpoint
        this.server.define_endpoint(
            "/account/",
            (resp) => {
                this.userInfo = resp;
                this.name = resp.name || '';
                this.show = true;
                this.showError = false;
                this.showSuccess = false;
                this.requestUpdate();
            },
            HTTP_GET
        );

        // Update name endpoint
        this.server.define_endpoint(
            "/account/",
            (resp) => {
                if (resp.success) {
                    this.showSuccess = true;
                    this.successMessage = 'Name updated successfully';
                    this.showError = false;

                    // Notify other components about the name change
                    multicall({
                        target: 'name_updated',
                        query: '[jsum]',
                        params: [resp]
                    });
                } else {
                    this.showError = true;
                    this.errorMessage = resp.message || 'Failed to update name';
                    this.showSuccess = false;
                }
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        // Update password endpoint
        this.server.define_endpoint(
            "/account/password",
            (resp) => {
                if (resp.success) {
                    this.showSuccess = true;
                    this.successMessage = 'Password updated successfully';
                    this.showError = false;
                    this.oldPassword = '';
                    this.newPassword = '';
                    this.confirmPassword = '';
                } else {
                    this.showError = true;
                    this.errorMessage = resp.message || 'Failed to update password';
                    this.showSuccess = false;
                }
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );
    }

    show_account_modal() {
        // Fetch current user information
        this.server.call("/account/", HTTP_GET);
    }

    hideModal() {
        this.show = false;
        this.clearForm();
    }

    clearForm() {
        this.oldPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
        this.showError = false;
        this.showSuccess = false;
    }

    updateName() {
        if (!this.name.trim()) {
            this.showError = true;
            this.errorMessage = 'Name is required';
            this.showSuccess = false;
            this.requestUpdate();
            return;
        }

        this.server.call("/account/", HTTP_POST_JSON, {
            name: this.name.trim()
        });
    }

    updatePassword() {
        // Validation
        if (!this.oldPassword) {
            this.showError = true;
            this.errorMessage = 'Current password is required';
            this.showSuccess = false;
            this.requestUpdate();
            return;
        }

        if (!this.newPassword) {
            this.showError = true;
            this.errorMessage = 'New password is required';
            this.showSuccess = false;
            this.requestUpdate();
            return;
        }

        if (this.newPassword !== this.confirmPassword) {
            this.showError = true;
            this.errorMessage = 'New passwords do not match';
            this.showSuccess = false;
            this.requestUpdate();
            return;
        }

        if (this.newPassword.length < 6) {
            this.showError = true;
            this.errorMessage = 'New password must be at least 6 characters long';
            this.showSuccess = false;
            this.requestUpdate();
            return;
        }

        this.server.call("/account/password", HTTP_POST_JSON, {
            old_password: this.oldPassword,
            new_password: this.newPassword
        });
    }

    handleSubmit(e) {
        e.preventDefault();
        // Form submission is handled by individual button clicks
    }
}

customElements.define('account-modal', AccountModal);