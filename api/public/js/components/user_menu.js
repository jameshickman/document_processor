import {BaseComponent} from '../lib/component_base.js';
import {multicall} from '../lib/jsum.js';
import {css, html} from "lit";

export class UserMenu extends BaseComponent {
    static properties = {
        userInfo: {type: Object},
        showDropdown: {type: Boolean}
    };

    constructor() {
        super();
        this.userInfo = null;
        this.showDropdown = false;
        
        // Listen for clicks outside to close dropdown
        document.addEventListener('click', (e) => this.handleDocumentClick(e));
    }

    static styles = css`
        :host {
            font-family: 'Verdana', 'Arial', 'Droid Sans', 'Lato', sans-serif;
        }

        .user-menu-container {
            position: relative;
            display: inline-block;
        }

        .user-button {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #ffffff;
            border: none;
            border-radius: 0;
            cursor: pointer;
            font-size: 13px;
            color: #495057;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
            min-width: 160px;
            height: 44px;
            justify-content: space-between;
        }

        .user-button:hover {
            background: #f8f9fa;
        }

        .user-info {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }

        .user-name {
            font-weight: 600;
            line-height: 1.2;
        }

        .user-email {
            font-size: 12px;
            color: #6c757d;
            line-height: 1.2;
        }

        .dropdown-icon {
            font-size: 12px;
            transition: transform 0.2s ease;
        }

        .dropdown-icon.open {
            transform: rotate(180deg);
        }

        .dropdown-menu {
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 4px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            min-width: 180px;
            z-index: 1001;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-8px);
            transition: all 0.2s ease;
        }

        .dropdown-menu.show {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }

        .menu-item {
            display: block;
            width: 100%;
            padding: 12px 16px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 14px;
            color: #495057;
            text-align: left;
            transition: background-color 0.15s ease;
            border-radius: 6px;
        }

        .menu-item:hover {
            background: #f8f9fa;
        }

        .logout-item {
            display: block;
            width: 100%;
            padding: 12px 16px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 14px;
            color: #dc3545;
            text-align: left;
            transition: background-color 0.15s ease;
            border-radius: 6px;
            border-top: 1px solid #dee2e6;
            margin-top: 4px;
        }

        .logout-item:hover {
            background: #f8f9fa;
            color: #c82333;
        }

        .hidden {
            display: none;
        }
    `;

    render() {
        if (!this.userInfo) {
            return html`<div class="hidden"></div>`;
        }

        return html`
            <div class="user-menu-container">
                <button 
                    class="user-button" 
                    @click="${this.toggleDropdown}"
                    aria-expanded="${this.showDropdown}"
                    aria-haspopup="true"
                >
                    <div class="user-info">
                        <div class="user-name">${this.userInfo.name || 'Unknown User'}</div>
                        <div class="user-email">${this.userInfo.email || ''}</div>
                    </div>
                    <span class="dropdown-icon ${this.showDropdown ? 'open' : ''}">▼</span>
                </button>
                
                <div class="dropdown-menu ${this.showDropdown ? 'show' : ''}">
                    <button class="menu-item" @click="${this.openAccountModal}">
                        Account Settings
                    </button>
                    <button class="logout-item" @click="${this.logout}">
                        Log Out
                    </button>
                </div>
            </div>
        `;
    }

    toggleDropdown(e) {
        e.stopPropagation();
        this.showDropdown = !this.showDropdown;
    }

    handleDocumentClick(e) {
        // Close dropdown if clicking outside
        if (!this.contains(e.target)) {
            this.showDropdown = false;
        }
    }

    openAccountModal() {
        // Close dropdown
        this.showDropdown = false;

        // Use multicall to send a message to the account modal to show itself
        multicall({
            target: 'show_account_modal',
            query: '[jsum]',
            params: []
        });
    }

    logout() {
        // Close dropdown
        this.showDropdown = false;

        // Reload the page to reset application state and trigger login modal
        window.location.reload();
    }

    login_success(user_information) {
        /**
         * Listen for the message from the login-modal
         * See the /auth/login endpoint for the fields returned on log-in
         * Expected fields: success, jwt, username, email, account_id
         */
        if (user_information && user_information.success) {
            this.userInfo = {
                name: user_information.username || 'Unknown User',
                email: user_information.email || ''
            };
            this.requestUpdate();
        }
    }

    name_updated(response) {
        /**
         * Listen for name updates from the account modal
         */
        if (response && response.success && this.userInfo) {
            this.userInfo.name = response.name || this.userInfo.name;
            this.requestUpdate();
        }
    }
}

customElements.define('user-menu', UserMenu);