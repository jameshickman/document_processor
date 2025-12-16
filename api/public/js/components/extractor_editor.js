import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON, HTTP_DELETE, HTTP_POST_FORM } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";


export class ExtractorEditor extends BaseComponent {
    static properties = {
        extractors: {type: Array, state: true},
        current_extractor: {type: Object, state: true},
        selected_extractor_id: {type: Number, state: true},
        loading: {type: Boolean, state: true},
        run_results: {type: Object, state: true},
        results_collapsed: {type: Boolean, state: true},
        creating_new: {type: Boolean, state: true},
        new_extractor_name: {type: String, state: true},
        renaming: {type: Boolean, state: true},
        rename_temp_name: {type: String, state: true},
        rename_original_name: {type: String, state: true}
    };
    static styles = css`
        .container {
            display: flex;
            gap: 20px;
            height: 90vh;
            padding: 10px;
            font-family: Arial, sans-serif;
            overflow: hidden;
        }
        
        .left-column,
        .middle-column,
        .right-column {
            display: flex;
            flex-direction: column;
            min-height: 0;
            height: 100%;
        }
        
        .left-column {
            max-width: 300px;
            flex: 0 0 300px;
        }
        
        .middle-column {
            flex: 1;
            max-width: 500px;
            transition: all 0.3s ease;
        }
        
        .container:has(.right-column.collapsed) .middle-column {
            max-width: none;
        }
        
        .right-column {
            flex: 1;
            transition: all 0.3s ease;
        }
        
        .right-column.collapsed {
            flex: 0 0 40px;
            min-width: 40px;
            max-width: 40px;
        }
        
        .panel {
            padding: 15px;
            display: flex;
            flex-direction: column;
            min-height: 0;
            height: 100%;
        }
        
        h3 {
            margin: 0 0 15px 0;
            font-size: 18px;
            font-weight: bold;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
        }
        
        .list-item {
            padding: 8px;
            margin: 5px 0;
            background: #f5f5f5;
            border: 1px solid #ddd;
            cursor: pointer;
            border-radius: 3px;
        }
        
        .list-item:hover {
            background: #e5e5e5;
        }
        
        .list-item.selected {
            background: #007bff;
            color: white;
        }
        
        .extractors-list {
            flex: 1;
            overflow-y: auto;
            min-height: 0;
        }
        
        .action-buttons {
            display: flex;
            gap: 5px;
            margin: 10px 0;
            flex-wrap: wrap;
            flex-shrink: 0;
        }
        
        .btn {
            padding: 6px 12px;
            border: 1px solid #ccc;
            background: #fff;
            cursor: pointer;
            border-radius: 3px;
            font-size: 12px;
        }
        
        .btn:hover {
            background: #f0f0f0;
        }
        
        .btn-primary {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }
        
        .btn-primary:hover {
            background: #0056b3;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
            border-color: #dc3545;
        }
        
        .prompt-editor {
            flex: 0 0 auto;
            margin-bottom: 15px;
        }
        
        .prompt-textarea {
            width: 100%;
            height: 120px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-family: monospace;
            resize: vertical;
        }
        
        .fields-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        
        .fields-list {
            flex: 1;
            overflow-y: auto;
            min-height: 0;
        }
        
        .field-row {
            position: relative;
            margin: 10px 0;
            padding: 10px;
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .field-delete-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 24px;
            height: 24px;
            padding: 0;
            border: none;
            background: #dc3545;
            color: white;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            line-height: 1;
        }
        
        .field-delete-btn:hover {
            background: #c82333;
        }
        
        .field-input {
            width: calc(100% - 35px);
            margin-bottom: 8px;
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 2px;
            font-family: inherit;
            resize: vertical;
        }
        
        .field-label {
            font-size: 12px;
            color: #666;
            font-weight: bold;
            margin-bottom: 4px;
        }
        
        .results-display {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
            flex: 1;
            overflow-y: auto;
            min-height: 0;
            max-width: 100%;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        
        .file-result {
            margin-bottom: 20px;
            padding: 10px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 3px;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        
        .file-result h4 {
            margin: 0 0 10px 0;
            color: #007bff;
            font-size: 16px;
        }
        
        .extraction-item {
            padding: 4px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .extraction-item:last-child {
            border-bottom: none;
        }
        
        .array-value {
            margin: 4px 0;
            padding-left: 20px;
        }
        
        .array-value li {
            margin: 2px 0;
        }
        
        .object-value {
            margin: 4px 0;
            padding-left: 15px;
            border-left: 2px solid #e0e0e0;
        }
        
        .object-item {
            margin: 2px 0;
            padding: 2px 0;
        }
        
        .null-value {
            color: #999;
            font-style: italic;
        }
        
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        
        .no-selection {
            color: #999;
            text-align: center;
            padding: 20px;
            font-style: italic;
        }
        
        .run-button {
            background: #28a745;
            color: white;
            border: 1px solid #28a745;
            padding: 10px 20px;
            font-weight: bold;
            margin-top: 15px;
            flex-shrink: 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .run-button:hover:not(:disabled) {
            background: #218838;
            border-color: #218838;
        }
        
        .run-button:disabled {
            background: #6c757d;
            border-color: #6c757d;
            color: #ffffff;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .header-with-toggle {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        
        .header-with-toggle h3 {
            margin: 0;
            border-bottom: none;
            padding-bottom: 0;
        }
        
        .collapse-toggle {
            background: #007bff;
            color: white;
            border: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            flex-shrink: 0;
        }
        
        .collapse-toggle:hover {
            background: #0056b3;
        }
        
        .panel.collapsed {
            padding: 5px;
        }
        
        .panel.collapsed > *:not(.collapse-toggle) {
            display: none;
        }
        
        .panel.collapsed .collapse-toggle {
            margin: 0 auto;
        }
        
        @keyframes flashBorder {
            0% { border-color: #007bff; box-shadow: 0 0 10px rgba(0, 123, 255, 0.5); }
            50% { border-color: #0056b3; box-shadow: 0 0 20px rgba(0, 123, 255, 0.8); }
            100% { border-color: #ddd; box-shadow: none; }
        }
        
        .flash-new {
            animation: flashBorder 2s ease-out;
        }
        
        .download-pdf-btn {
            background: #17a2b8;
            color: white;
            border: 1px solid #17a2b8;
            padding: 4px 8px;
            font-size: 11px;
            border-radius: 3px;
            cursor: pointer;
            margin-top: 8px;
            margin-right: 8px;
            display: inline-block;
            text-decoration: none;
        }
        
        .download-pdf-btn:hover {
            background: #138496;
            border-color: #117a8b;
        }
        
        .download-pdf-btn:disabled {
            background: #6c757d;
            border-color: #6c757d;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .file-result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .file-result-title {
            margin: 0;
            color: #007bff;
            font-size: 16px;
        }
        
        .download-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .inline-edit-item {
            padding: 8px;
            margin: 5px 0;
            background: #fffbcc;
            border: 2px solid #ffc107;
            border-radius: 3px;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .inline-edit-input {
            padding: 6px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 14px;
            width: 100%;
        }

        .inline-edit-buttons {
            display: flex;
            gap: 5px;
        }

        .inline-edit-buttons .btn {
            flex: 1;
            padding: 4px 8px;
            font-size: 12px;
        }

        .header-with-name {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
        }

        .header-with-name h3 {
            margin: 0;
            border-bottom: none;
            padding-bottom: 0;
            font-size: 14px;
            color: #666;
        }

        .extractor-name-display {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }

        .extractor-name-edit {
            display: flex;
            flex-direction: column;
            gap: 5px;
            margin-top: 5px;
            flex: 1;
        }

        .extractor-name-input {
            padding: 6px;
            border: 2px solid #007bff;
            border-radius: 3px;
            font-size: 16px;
            font-weight: bold;
        }

        .rename-buttons {
            display: flex;
            gap: 5px;
        }

        .list-item.disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    `;

    #currentRunFiles = new Map(); // Map of file ID -> file info

    constructor() {
        super();
        this.extractors = [];
        this.current_extractor = null;
        this.selected_extractor_id = null;
        this.loading = false;
        this.run_results = null;
        this.results_collapsed = false;
        this.creating_new = false;
        this.new_extractor_name = '';
        this.renaming = false;
        this.rename_temp_name = '';
        this.rename_original_name = '';
    }

    server_interface(api) {
        this.init_server(api);
        
        // Load extractors list
        this.server.define_endpoint(
            "/extractors",
            (resp) => {
                this.extractors = resp;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_GET
        );
        
        // Load specific extractor details
        this.server.define_endpoint(
            "/extractors/{id}",
            (resp) => {
                this.current_extractor = resp;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_GET
        );
        
        // Save extractor
        this.server.define_endpoint(
            "/extractors/{id}",
            (resp) => {
                // If creating new, auto-select it
                if (resp && resp.id && !this.selected_extractor_id) {
                    this.selected_extractor_id = resp.id;
                    this.#load_extractor(resp.id);
                } else if (this.selected_extractor_id) {
                    // Reload current extractor to get updated name
                    this.#load_extractor(this.selected_extractor_id);
                }
                this.#load_extractors();
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );
        
        // Run extractor against files
        this.server.define_endpoint(
            "/extractors/run/{extractor_id}/{document_id}",
            (resp) => {
                // Handle multiple file results by accumulating them
                if (!this.run_results || this.run_results.loading) {
                    this.run_results = { files: [] };
                }
                
                // Extract document ID from the response
                const documentId = resp.document_id ? resp.document_id.toString() : null;
                
                // Find the file info using the map
                const fileInfo = documentId ? this.#currentRunFiles.get(documentId) : null;
                
                if (!fileInfo) {
                    console.error("Cannot find file for document_id:", documentId);
                    return;
                }

                // Add new result
                this.run_results.files.push({
                    fileName: fileInfo.name,
                    fileId: fileInfo.id,
                    results: resp.result
                });

                this.requestUpdate();
            },
            HTTP_GET
        );
        
        // Delete extractor endpoint
        this.server.define_endpoint(
            "/extractors/{id}",
            (resp) => {
                this.current_extractor = null;
                this.selected_extractor_id = null;
                this.#load_extractors();
                this.requestUpdate();
            },
            HTTP_DELETE
        );
        
        // Note: Export now uses direct API download method instead of endpoint callback
        
        // Import extractor endpoint
        this.server.define_endpoint(
            "/extractors/import",
            (resp) => {
                alert("Extractor imported successfully!");
                this.#load_extractors();
                this.requestUpdate();
            },
            HTTP_POST_FORM
        );
    }

    login_success() {
        this.#load_extractors();
    }

    #load_extractors() {
        this.loading = true;
        this.server.call("/extractors", HTTP_GET);
    }

    #load_extractor(extractor_id) {
        this.loading = true;
        this.selected_extractor_id = extractor_id;
        this.server.call("/extractors/{id}", HTTP_GET, null, null, {id: extractor_id});
    }

    // UI event handlers
    #create_extractor_clicked(e) {
        if (this.creating_new) return;
        this.creating_new = true;
        this.new_extractor_name = '';
        this.requestUpdate();

        this.updateComplete.then(() => {
            const input = this.shadowRoot.querySelector('.inline-edit-input');
            if (input) input.focus();
        });
    }

    #new_extractor_name_changed(e) {
        this.new_extractor_name = e.target.value;
    }

    #save_new_extractor_clicked(e) {
        const name = this.new_extractor_name.trim();
        if (!name) {
            alert("Extractor name cannot be empty");
            return;
        }

        this.creating_new = false;
        this.new_extractor_name = '';

        const newExtractor = {
            name: name,
            prompt: "",
            fields: []
        };
        this.server.call("/extractors/{id}", HTTP_POST_JSON, newExtractor, null, {id: 0});
    }

    #cancel_new_extractor_clicked(e) {
        this.creating_new = false;
        this.new_extractor_name = '';
        this.requestUpdate();
    }

    #new_extractor_keydown(e) {
        if (e.key === 'Enter') {
            this.#save_new_extractor_clicked(e);
        } else if (e.key === 'Escape') {
            this.#cancel_new_extractor_clicked(e);
        }
    }

    #rename_extractor_clicked(e) {
        if (!this.selected_extractor_id || !this.current_extractor || this.renaming) return;

        this.renaming = true;
        this.rename_temp_name = this.current_extractor.name;
        this.rename_original_name = this.current_extractor.name;
        this.requestUpdate();

        this.updateComplete.then(() => {
            const input = this.shadowRoot.querySelector('.extractor-name-input');
            if (input) {
                input.focus();
                input.select();
            }
        });
    }

    #rename_name_changed(e) {
        this.rename_temp_name = e.target.value;
    }

    #save_rename_clicked(e) {
        const newName = this.rename_temp_name.trim();
        if (!newName) {
            alert("Extractor name cannot be empty");
            return;
        }

        if (newName === this.rename_original_name) {
            this.renaming = false;
            this.rename_temp_name = '';
            this.rename_original_name = '';
            this.requestUpdate();
            return;
        }

        this.current_extractor.name = newName;
        this.renaming = false;
        this.rename_temp_name = '';
        this.rename_original_name = '';

        const updatedExtractor = {...this.current_extractor, name: newName};
        this.server.call("/extractors/{id}", HTTP_POST_JSON, updatedExtractor, null, {id: this.selected_extractor_id});
    }

    #cancel_rename_clicked(e) {
        this.renaming = false;
        this.rename_temp_name = '';
        this.rename_original_name = '';
        this.requestUpdate();
    }

    #rename_keydown(e) {
        if (e.key === 'Enter') {
            this.#save_rename_clicked(e);
        } else if (e.key === 'Escape') {
            this.#cancel_rename_clicked(e);
        }
    }

    #delete_extractor_clicked(e) {
        if (this.selected_extractor_id) {
            const extractorName = this.extractors.find(e => e.id === this.selected_extractor_id)?.name || "this extractor";
            if (confirm(`Are you sure you want to delete "${extractorName}"? This action cannot be undone.`)) {
                this.server.call("/extractors/{id}", HTTP_DELETE, null, null, {id: this.selected_extractor_id});
            }
        }
    }

    #extractor_clicked(e) {
        if (this.creating_new || this.renaming) return;
        const id = parseInt(e.target.dataset.extractorId);
        this.#load_extractor(id);
    }

    #prompt_changed(e) {
        if (this.current_extractor) {
            this.current_extractor.prompt = e.target.value;
            this.requestUpdate();
        }
    }

    #create_field_clicked(e) {
        if (!this.current_extractor) return;
        
        const newField = { name: '', description: '' };
        this.current_extractor.fields = [...this.current_extractor.fields, newField];
        this.requestUpdate();
        
        // Scroll to bottom and flash the new field after update completes
        this.updateComplete.then(() => {
            const fieldsList = this.shadowRoot.querySelector('.fields-list');
            if (fieldsList) {
                fieldsList.scrollTop = fieldsList.scrollHeight;
                
                // Flash the last (newest) field row
                const fieldRows = this.shadowRoot.querySelectorAll('.field-row');
                const lastFieldRow = fieldRows[fieldRows.length - 1];
                if (lastFieldRow) {
                    lastFieldRow.classList.add('flash-new');
                    // Remove the class after animation completes
                    setTimeout(() => {
                        lastFieldRow.classList.remove('flash-new');
                    }, 2000);
                }
            }
        });
    }

    #delete_field_clicked(e) {
        if (!this.current_extractor) return;
        
        const fieldIndex = parseInt(e.target.dataset.fieldIndex);
        this.current_extractor.fields = this.current_extractor.fields.filter((_, index) => index !== fieldIndex);
        this.requestUpdate();
    }

    #field_changed(e) {
        if (!this.current_extractor) return;
        
        const fieldIndex = parseInt(e.target.dataset.fieldIndex);
        const field = e.target.dataset.field;
        const value = e.target.value;
        
        if (field === 'name') {
            this.current_extractor.fields[fieldIndex].name = value;
        } else if (field === 'description') {
            this.current_extractor.fields[fieldIndex].description = value;
        }
        
        this.requestUpdate();
    }

    #save_clicked(e) {
        if (this.current_extractor && this.selected_extractor_id) {
            this.server.call("/extractors/{id}", HTTP_POST_JSON, this.current_extractor, null, {id: this.selected_extractor_id});
        }
    }

    #export_extractor_clicked(e) {
        if (this.selected_extractor_id) {
            // Use the enhanced download method from API.js library
            const exportUrl = `/extractors/export/${this.selected_extractor_id}`;
            this.server.download(
                exportUrl,
                null, // no content, using URL
                'extractor_export.yaml', // default filename
                null, // auto-detect MIME type
                (filename) => {
                    console.log(`Extractor exported as: ${filename}`);
                },
                (error) => {
                    console.error('Export failed:', error);
                    alert('Export failed. Please try again.');
                }
            );
        }
    }

    #import_extractor_clicked(e) {
        // Create a hidden file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.yaml,.yml';
        fileInput.style.display = 'none';
        
        fileInput.onchange = (event) => {
            const inputElement = event.target;
            if (inputElement.files && inputElement.files.length > 0) {
                // Call the import endpoint - API.js will handle FormData creation
                this.server.call("/extractors/import", HTTP_POST_FORM, {
                    file: inputElement
                });
            }
        };
        
        document.body.appendChild(fileInput);
        fileInput.click();
        document.body.removeChild(fileInput);
    }

    #toggle_results_column(e) {
        this.results_collapsed = !this.results_collapsed;
    }

    #download_marked_pdf_clicked(e) {
        const fileId = e.target.dataset.fileId;
        const fileName = e.target.dataset.fileName;
        
        if (!fileId || !this.selected_extractor_id) {
            alert("Unable to download: missing file or extractor information");
            return;
        }
        
        // Use API.js download method for authenticated download
        const downloadUrl = `/documents/marked/${this.selected_extractor_id}/${fileId}`;
        const defaultFilename = `${fileName}_marked_extractor_${this.selected_extractor_id}.pdf`;
        
        this.server.download(
            downloadUrl,
            null, // no content, using URL
            defaultFilename,
            'application/pdf',
            (filename) => {
                console.log(`Marked PDF downloaded: ${filename}`);
            },
            (error) => {
                console.error('Download failed:', error);
                if (error.message && error.message.includes('404')) {
                    alert('Marked PDF not found. Please run the extraction again to generate a marked version.');
                } else {
                    alert('Download failed. Please try again or check that the marked PDF exists.');
                }
            }
        );
    }

    #renderExtractionValue(value) {
        if (value === null || value === undefined) {
            return html`<span class="null-value">null</span>`;
        }
        
        if (Array.isArray(value)) {
            return html`
                <ul class="array-value">
                    ${value.map(item => html`<li>${this.#renderExtractionValue(item)}</li>`)}
                </ul>
            `;
        }
        
        if (typeof value === 'object') {
            return html`
                <div class="object-value">
                    ${Object.entries(value).map(([key, val]) => html`
                        <div class="object-item">
                            <strong>${key}:</strong> ${this.#renderExtractionValue(val)}
                        </div>
                    `)}
                </div>
            `;
        }
        
        return html`${value}`;
    }

    async #run_against_files_clicked(e) {
        if (!this.selected_extractor_id) {
            alert("Please select an extractor first");
            return;
        }
        
        try {
            const selectedFilesResult = await multicall({
                target: "get_selected_files",
                query: "[jsum='files_list']",
                params: []
            });
            
            if (!selectedFilesResult || selectedFilesResult.length === 0 || !selectedFilesResult[0].result) {
                alert("Files list widget not found or no method results");
                return;
            }
            
            const selectedFiles = selectedFilesResult[0].result;
            if (!selectedFiles || selectedFiles.length === 0) {
                alert("Please select files to run against");
                return;
            }
            
            // Clear any previous results and reset file tracking
            this.run_results = { loading: true, expectedFiles: selectedFiles.length };
            this.#currentRunFiles.clear();
            this.requestUpdate();
            
            // Store file information for display using ID as key
            selectedFiles.forEach(file => {
                this.#currentRunFiles.set(file.id.toString(), file);
            });
            
            // Run extraction against all selected files in parallel
            selectedFiles.forEach(file => {
                this.server.call("/extractors/run/{extractor_id}/{document_id}", HTTP_GET, null, null, {
                    extractor_id: this.selected_extractor_id,
                    document_id: file.id
                });
            });
            
        } catch (error) {
            console.error("Error running extractor:", error);
            this.run_results = { error: "Error running extractor against files" };
            this.requestUpdate();
        }
    }

    render() {
        return html`
            <div class="container">
                <!-- Left Column: Extractors List -->
                <div class="left-column">
                    <div class="panel">
                        <h3>Extractors</h3>
                        
                        ${this.loading ? html`<div class="loading">Loading...</div>` : ''}

                        <div class="extractors-list">
                            ${this.creating_new ? html`
                                <div class="inline-edit-item">
                                    <input
                                        type="text"
                                        class="inline-edit-input"
                                        .value=${this.new_extractor_name}
                                        @input=${this.#new_extractor_name_changed}
                                        @keydown=${this.#new_extractor_keydown}
                                        placeholder="Enter extractor name..."
                                    />
                                    <div class="inline-edit-buttons">
                                        <button class="btn btn-primary" @click=${this.#save_new_extractor_clicked}>Save</button>
                                        <button class="btn" @click=${this.#cancel_new_extractor_clicked}>Cancel</button>
                                    </div>
                                </div>
                            ` : ''}

                            ${this.extractors.map(extractor => html`
                                <div
                                    class="list-item ${this.selected_extractor_id === extractor.id ? 'selected' : ''} ${this.creating_new || this.renaming ? 'disabled' : ''}"
                                    data-extractor-id=${extractor.id}
                                    @click=${this.creating_new || this.renaming ? null : this.#extractor_clicked}
                                >
                                    ${extractor.name}
                                </div>
                            `)}
                        </div>
                        
                        <div class="action-buttons">
                            <button class="btn btn-primary" @click=${this.#create_extractor_clicked} ?disabled=${this.creating_new || this.renaming}>Create New</button>
                            <button class="btn" @click=${this.#rename_extractor_clicked} ?disabled=${!this.selected_extractor_id || this.creating_new || this.renaming}>Rename</button>
                            <button class="btn btn-danger" @click=${this.#delete_extractor_clicked} ?disabled=${!this.selected_extractor_id || this.creating_new || this.renaming}>Delete</button>
                            <button class="btn" @click=${this.#export_extractor_clicked} ?disabled=${!this.selected_extractor_id || this.creating_new || this.renaming}>Export</button>
                            <button class="btn" @click=${this.#import_extractor_clicked} ?disabled=${this.creating_new || this.renaming}>Import</button>
                        </div>
                    </div>
                </div>

                <!-- Middle Column: Extractor Editor -->
                <div class="middle-column">
                    <div class="panel">
                        ${!this.current_extractor ? html`
                            <h3>Extractor Editor</h3>
                            <div class="no-selection">Select an extractor to edit</div>
                        ` : html`
                            <div class="header-with-name">
                                <div style="flex: 1;">
                                    <h3>Extractor Editor</h3>
                                    ${this.renaming ? html`
                                        <div class="extractor-name-edit">
                                            <input
                                                type="text"
                                                class="extractor-name-input"
                                                .value=${this.rename_temp_name}
                                                @input=${this.#rename_name_changed}
                                                @keydown=${this.#rename_keydown}
                                            />
                                            <div class="rename-buttons">
                                                <button class="btn btn-primary" @click=${this.#save_rename_clicked}>Save</button>
                                                <button class="btn" @click=${this.#cancel_rename_clicked}>Cancel</button>
                                            </div>
                                        </div>
                                    ` : html`
                                        <div class="extractor-name-display">${this.current_extractor.name}</div>
                                    `}
                                </div>
                            </div>

                            <!-- Prompt Editor -->
                            <div class="prompt-editor">
                                    <div class="field-label">Prompt:</div>
                                    <textarea 
                                        class="prompt-textarea" 
                                        .value=${this.current_extractor.prompt}
                                        @input=${this.#prompt_changed}
                                        placeholder="Enter the extraction prompt..."
                                    ></textarea>
                                </div>
                                
                                <!-- Fields Section -->
                                <div class="fields-section">
                                    <div class="field-label">Fields:</div>
                                    <div class="fields-list">
                                        ${this.current_extractor.fields?.map((field, index) => html`
                                            <div class="field-row">
                                                <button 
                                                    class="field-delete-btn" 
                                                    data-field-index=${index}
                                                    @click=${this.#delete_field_clicked}
                                                    title="Delete field"
                                                >✕</button>
                                                
                                                <div class="field-label">Name:</div>
                                                <input 
                                                    type="text" 
                                                    class="field-input" 
                                                    .value=${field.name}
                                                    data-field-index=${index}
                                                    data-field="name"
                                                    @input=${this.#field_changed}
                                                    placeholder="Field name..."
                                                />
                                                
                                                <div class="field-label">Description:</div>
                                                <textarea 
                                                    class="field-input" 
                                                    .value=${field.description}
                                                    data-field-index=${index}
                                                    data-field="description"
                                                    @input=${this.#field_changed}
                                                    placeholder="Field description..."
                                                    rows="3"
                                                ></textarea>
                                            </div>
                                        `) || ''}
                                    </div>
                                    
                                    <div class="action-buttons">
                                        <button class="btn btn-primary" @click=${this.#create_field_clicked} ?disabled=${this.renaming}>Add Field</button>
                                        <button class="btn btn-primary" @click=${this.#save_clicked} ?disabled=${this.renaming}>Save Extractor</button>
                                    </div>
                                </div>
                            `
                        }
                    </div>
                </div>

                <!-- Right Column: Testing Area -->
                <div class="right-column ${this.results_collapsed ? 'collapsed' : ''}">
                    <div class="panel ${this.results_collapsed ? 'collapsed' : ''}">
                        ${!this.results_collapsed ? html`
                            <div class="header-with-toggle">
                                <h3>Test Extractor</h3>
                                <button class="collapse-toggle" @click=${this.#toggle_results_column} title="Collapse results">→</button>
                            </div>` : html`
                            <button class="collapse-toggle" @click=${this.#toggle_results_column} title="Expand results">←</button>`}
                        
                        ${!this.results_collapsed ? html`
                            
                            <button class="btn run-button" @click=${this.#run_against_files_clicked} ?disabled=${!this.selected_extractor_id}>Run against selected files</button>
                            
                            ${this.run_results && !this.run_results.loading ? 
                            html`
                                <div class="results-display">
                                    ${this.run_results.files ? 
                                        // Multiple file results
                                        this.run_results.files.map((fileResult, index) => html`
                                            <div class="file-result">
                                                <div class="file-result-header">
                                                    <h4 class="file-result-title">${fileResult.fileName} Results:</h4>
                                                    <div class="download-actions">
                                                        ${fileResult.results && fileResult.results.found ? html`
                                                            <button 
                                                                class="download-pdf-btn"
                                                                data-file-id="${fileResult.fileId}"
                                                                data-file-name="${fileResult.fileName.replace(/\.[^/.]+$/, '')}"
                                                                @click=${this.#download_marked_pdf_clicked}
                                                                title="Download marked PDF with highlighted citations"
                                                            >
                                                                📄 Download Marked PDF
                                                            </button>
                                                        ` : html`
                                                            <button 
                                                                class="download-pdf-btn" 
                                                                disabled
                                                                title="No data found - marked PDF not available"
                                                            >
                                                                📄 No Marked PDF
                                                            </button>
                                                        `}
                                                    </div>
                                                </div>
                                                ${fileResult.results ? html`
                                                    <div><strong>Found:</strong> ${fileResult.results.found ? 'Yes' : 'No'}</div>
                                                    <div><strong>Confidence:</strong> ${fileResult.results.confidence}</div>
                                                    ${fileResult.results.explanation ? html`
                                                        <div><strong>Explanation:</strong> ${fileResult.results.explanation}</div>
                                                    ` : ''}
                                                    ${fileResult.results.extracted_data ? html`
                                                        <div><strong>Extracted Data:</strong></div>
                                                        ${Object.entries(fileResult.results.extracted_data).map(([key, value]) => html`
                                                            <div class="extraction-item"><strong>${key}:</strong> ${this.#renderExtractionValue(value)}</div>
                                                        `)}
                                                    ` : ''}
                                                ` : html`<div>No results</div>`}
                                            </div>
                                        `) :
                                        html`<div class="no-selection">No results to display</div>`
                                    }
                                </div>
                            ` :
                                this.run_results && this.run_results.loading ?
                                html`<div class="results-display loading">Running extraction...</div>` :
                                html`<div class="results-display no-selection">Run an extractor to see results here</div>`
                            }
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
}

customElements.define('extractor-editor', ExtractorEditor);