import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_FORM } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";

export class FilesList extends BaseComponent {
    static properties = {
        files: {type: Array, state: true},
        form_element_file: {type: HTMLElement, state: true},
    };

    static styles = css`
        .container {
            display: flex;flex-direction: column;
            height: 100%;
        }
        .header {
            flex-grow: 0;
        }
        #files-list {
            flex-grow: 1;
            overflow-y: auto;
        }
        .upload-form {
            flex-grow: 0;
        }
    `;

    constructor() {
        super();
        this.files = [];
        this.form_element_file = null;
    }

    server_interface(api) {
        this.init_server(api);
        this.server.define_endpoint(
            "/documents",
            (resp) => {
                this.files = resp.data;
                this.requestUpdate();
            },
            HTTP_GET
        );
        this.server.define_endpoint(
            "/documents",
            (res) => {
                this.#get_files();
            },
            HTTP_POST_FORM
        );
    };

    #get_files() {
        this.server.call(
            "/documents",
            HTTP_GET
        );
    }

    login_success(resp) {
        this.#get_files();
    };

    form_element_file_changed(e) {
        this.form_element_file = e.target;
    };

    upload_button_clicked(e) {
        e.preventDefault();
        if (!this.form_element_file || this.form_element_file.files.length === 0) {
            return;
        }
        this.server.call(
            "/documents",
            HTTP_POST_FORM,
            {
                file: this.form_element_file
            }
        )
    };

    file_item_clicked(e) {
        const file_id = e.currentTarget.dataset.fileId;
        multicall({
            'target': 'file_selected',
            'query': '[jsum]',
            'params': [file_id]
        });
    };

    render() {
        return html`
            <div class="container">
                <h1 class="header">Files List</h1>
                <ul id="files-list">
                    ${this.files.map((f) => html`
                        <li>
                            <button data-file-id="${f.id}" @click=${this.file_item_clicked}>
                                ${f.name}
                            </button>
                        </li>
                    `)}
                </ul>
                <div class="upload-form">
                    <form id="upload-form" class="form">
                        <input type="file" name="file" @input=${this.form_element_file_changed} />
                        <button @click=${this.upload_button_clicked}>Upload</button>
                    </form>
                </div>
            </div>
        `;
    }
}

customElements.define('files-list', FilesList);