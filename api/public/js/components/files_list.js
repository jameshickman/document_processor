import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_FORM, HTTP_DELETE } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";

export class FilesList extends BaseComponent {
    static properties = {
        files: {type: Array, state: true},
        form_element_file: {type: HTMLElement, state: true},
        upload_progress: {type: Number, state: true},
        uploading: {type: Boolean, state: true},
        has_selected_files: {type: Boolean, state: true}
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
        
        .upload-form button:disabled {
            background: #6c757d;
            border-color: #6c757d;
            cursor: not-allowed;
        }
        
        .progress-container {
            margin: 10px 0;
            display: none;
        }
        
        .progress-container.show {
            display: block;
        }
        
        .progress-bar-wrapper {
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #007bff, #0056b3);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 10px;
        }
        
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 12px;
            font-weight: bold;
            color: #333;
            z-index: 1;
        }
        
        .delete-selected-btn {
            background: #dc3545;
            color: white;
            border: 1px solid #dc3545;
            padding: 8px 16px;
            font-size: 14px;
            border-radius: 3px;
            cursor: pointer;
            margin-top: 10px;
            width: 100%;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .delete-selected-btn:hover:not(:disabled) {
            background: #c82333;
            border-color: #c82333;
        }
        
        .delete-selected-btn:disabled {
            background: #6c757d;
            border-color: #6c757d;
            cursor: not-allowed;
            opacity: 0.6;
        }
    `;

    constructor() {
        super();
        this.files = [];
        this.form_element_file = null;
        this.upload_progress = 0;
        this.uploading = false;
        this.has_selected_files = false;
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
                this.uploading = false;
                this.upload_progress = 0;
                this.#get_files();
                this.requestUpdate();
            },
            HTTP_POST_FORM
        );
        
        // Delete document endpoint
        this.server.define_endpoint(
            "/documents/{id}",
            (res) => {
                this.#get_files();
                this.requestUpdate();
            },
            HTTP_DELETE
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

    #update_selection_state() {
        const els_selected_files = this.renderRoot.querySelectorAll("#files-list input[type=checkbox]:checked");
        this.has_selected_files = els_selected_files.length > 0;
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

    file_item_clicked(e) {
        // Update selection state when checkbox is clicked
        setTimeout(() => this.#update_selection_state(), 0);
    };

    #delete_selected_clicked(e) {
        const selectedFiles = this.get_selected_files();
        
        if (selectedFiles.length === 0) {
            alert("Please select files to delete");
            return;
        }
        
        const fileNames = selectedFiles.map(f => f.name).join(", ");
        const confirmMessage = selectedFiles.length === 1 
            ? `Are you sure you want to delete "${fileNames}"?`
            : `Are you sure you want to delete ${selectedFiles.length} files: ${fileNames}?`;
        
        if (confirm(confirmMessage)) {
            // Delete each selected file
            selectedFiles.forEach(file => {
                this.server.call("/documents/{id}", HTTP_DELETE, null, null, {id: file.id});
            });
        }
    };

    upload_button_clicked(e) {
        e.preventDefault();
        if (!this.form_element_file || this.form_element_file.files.length === 0) {
            return;
        }
        
        // Start upload with progress tracking
        this.uploading = true;
        this.upload_progress = 0;
        this.requestUpdate();
        
        // Use the enhanced call method with progress callback
        this.server.call(
            "/documents",
            HTTP_POST_FORM,
            {
                file: this.form_element_file
            },
            null, // headers
            null, // path_vars
            false, // is_retry
            (percent, loaded, total) => {
                // Progress callback
                this.upload_progress = Math.round(percent);
                this.requestUpdate();
            }
        );
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
                        <button @click=${this.upload_button_clicked} ?disabled=${this.uploading}>
                            ${this.uploading ? 'Uploading...' : 'Upload'}
                        </button>
                        <div class="progress-container ${this.uploading ? 'show' : ''}">
                            <div class="progress-bar-wrapper">
                                <div class="progress-bar" style="width: ${this.upload_progress}%"></div>
                                <div class="progress-text">${this.upload_progress}%</div>
                            </div>
                        </div>
                    </form>
                    <button 
                        class="delete-selected-btn"
                        @click=${this.#delete_selected_clicked}
                        ?disabled=${!this.has_selected_files}
                    >
                        Delete Selected Files
                    </button>
                </div>
            </div>
        `;
    }
}

customElements.define('files-list', FilesList);