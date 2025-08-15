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
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .header {
            flex-grow: 0;
        }
        #files-list {
            border: 0;
            padding: 0;
            margin: 0;
            flex-grow: 1;
            overflow: auto;
            max-width: 25rem;
        }
        .files-list li {
            list-style: none;
            border: 0;
            padding: 0;
            margin: 0;
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
                this.files = resp;
                this.form_element_file.value = '';
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

    get_selected_files() {
        const file_ids = [];
        const els_selected_files = this.renderRoot.querySelectorAll("#files-list input[type=checkbox]:checked");
        for (const el_checkbox of els_selected_files) {
            file_ids.push(el_checkbox.dataset.fileId);
        }
        return file_ids;
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

    render() {
        return html`
            <div class="container">
                <h1 class="header">Files List</h1>
                <ul id="files-list">
                    ${this.files.map((f) => html`
                        <li>
                            <nobr>
                                <input 
                                        type="checkbox"
                                        id="check_${f.id}"
                                        data-file-id="${f.id}" 
                                        @click=${this.file_item_clicked} 
                                />
                                <label for="check_${f.id}">${f.name}</label>
                            </nobr>
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