import {BaseComponent} from '../lib/component_base.js';
import {HTTP_POST_FORM} from '../lib/API.js';
import {multicall} from '../lib/jsum.js';
import {css, html} from "lit";

export class LoginModal extends BaseComponent {
    static properties = {
        show: {type: Boolean},
        show_error: {type: Boolean},
        username: {type: String},
        password: {type: String}
    };

    // Templating
    static styles = css`
        #modal {
            display: flex;
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
        }
        .modal-window {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
        }
        .modal-header {
            font-size: 1.2em;
            font-weight: bold;
        }
    `;

    constructor() {
        super();
        this.show = true;
        this.show_error = false;
    }

    // JSUM listeners
    server_interface(api) {
        this.init_server(api);
        this.server.define_endpoint(
            "/login",
            (response) => {
                if (response.success) {
                    this.show = false;
                    this.dispatchEvent(new CustomEvent('login', {detail: response.data}));
                    this.username = '';
                    this.password = '';
                    multicall(
                        {
                            "target": "login_success",
                            "query": ".login-listen",
                            "params": [response]
                        }
                    ).then((results) => {
                        // For now, just log the results
                        console.log(results);
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
    async handle_submit(e) {
        e.preventDefault();
        this.show_error = false;
        this.server.call(
            "/login",
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
            <div id="modal" ?hidden=${!this.show}>
                <div class="modal-window">
                    <div class="modal-header">Log-in</div>
                    <p id="error" ?hidden=${!this.show_error}>Invalid username or password</p>
                    <div class="modal-body">
                        <form id="login-form" class="form">
                            <div class="form-group">
                                <label for="username">Username</label>
                                <input type="text" id="username" name="username" value=${this.username} required />
                                <label for="password">Password</label>
                                <input type="password" id="password" name="password" value=${this.password} required />
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