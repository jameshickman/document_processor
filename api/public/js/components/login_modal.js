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
            z-index: 1;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.4);
            backdrop-filter: blur(10px);
        }
        #modal.show {
            display: flex;
        }
        #modal.hide {
            display: none;
        }
        .modal-window {
            background-color: #fefefe;
            margin: auto auto;
            padding: 20px;
            border: 1px solid #888;
            max-width: 20rem;
        }
        .modal-header {
            font-size: 1.2em;
            font-weight: bold;
        }
        label {
            display: block;
            margin-bottom: 5px;
        }
        button {
            margin-top: 10px;
            display: block;
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