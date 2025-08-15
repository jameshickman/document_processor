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
            max-height: 90vh;
            padding: 15px;
            font-family: Arial, sans-serif;
            max-width: 350px;
            background: white;
            overflow: hidden;
        }
        
        .header {
            margin: 0 0 15px 0;
            font-size: 18px;
            font-weight: bold;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
        }
        
        #files-list {
            border: 0;
            padding: 0;
            margin: 0 0 20px 0;
            flex-grow: 1;
            overflow: auto;
            list-style: none;
        }
        
        #files-list li {
            list-style: none;
            border: 0;
            padding: 8px;
            margin: 5px 0;
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        
        #files-list li:hover {
            background: #e5e5e5;
        }
        
        #files-list li nobr {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        #files-list input[type="checkbox"] {
            margin: 0;
            cursor: pointer;
        }
        
        #files-list label {
            cursor: pointer;
            flex-grow: 1;
            font-size: 14px;
            color: #333;
        }
        
        .upload-form {
            border-top: 1px solid #ddd;
            padding-top: 15px;
        }
        
        .upload-form input[type="file"] {
            width: 100%;
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 3px;
            margin-bottom: 10px;
        }
        
        .upload-form button {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #007bff;
            background: #007bff;
            color: white;
            cursor: pointer;
            border-radius: 3px;
            font-size: 14px;
        }
        
        .upload-form button:hover {
            background: #0056b3;
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
        const selected_files = [];
        const els_selected_files = this.renderRoot.querySelectorAll("#files-list input[type=checkbox]:checked");
        for (const el_checkbox of els_selected_files) {
            const fileId = el_checkbox.dataset.fileId;
            // Find the file object to get the name
            const file = this.files.find(f => f.id.toString() === fileId);
            selected_files.push({
                id: fileId,
                name: file ? file.name : `File ${fileId}`
            });
        }
        return selected_files;
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
                <h3 class="header">Files List</h3>
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