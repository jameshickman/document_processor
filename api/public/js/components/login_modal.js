import {BaseComponent} from '../lib/component_base.js';
import {HTTP_POST_FORM} from '../lib/API.js';
import {multicall} from '../lib/jsum.js';
import {css, html} from "lit";

export class LoginModal extends BaseComponent {
    static properties = {
        show: {type: Boolean},
        show_error: {type: Boolean},
        username: {type: String, state: true},
        password: {type: String, state: true}
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
    `;

    constructor() {
        super();
        this.show = true;
        this.show_error = false;
        this.username = '';
        this.password = '';
    }

    login_success(resp) {
        this.username = '';
        this.password = '';
        this.show = false;
        this.dispatchEvent(new CustomEvent('login', {detail: {username: this.username}}));
        this.requestUpdate();
    }

    // JSUM listeners
    server_interface(api) {
        this.init_server(api);
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