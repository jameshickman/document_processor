import {BaseComponent} from '../lib/component_base.js';
import {HTTP_POST_FORM} from '../lib/API.js';
import {multicall} from '../lib/jsum.js';
import {css, html} from "/static/node_modules/lit/index.js";
import {classMap} from '/static/node_modules/lit/directives/class-map.js';

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
            display: none;
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
        .show_modal {
            display: flex;
        }
        #error {
            display: none;
        }
        .show_error {
            display: block;
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
        this.server_operations_setup();
    }

    // JSUM listeners
    server_interface(api) {
        self.init_server(api);
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

    // Setup server operations
    server_operations_setup() {
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
    };

    render() {
        const modal_classes = {
            show_modal: this.show
        };
        const error_classes = {
            show_error: this.show_error
        };
        return html`
            <div id="modal" class=${classMap(modal_classes)} jsum>
                <div class="modal-window">
                    <div class="modal-header">Log-in</div>
                    <p id="error" class=${classMap(error_classes)}>Invalid username or password</p>
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