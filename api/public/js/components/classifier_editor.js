import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";

export class ClassifierEditor extends BaseComponent {
    static properties = {
        classifier_sets: {type: Array, state: true},
        current_classifier_set: {type: Object, state: true},
        current_classifier: {type: Object, state: true},
        selected_classifier_set_id: {type: Number, state: true},
        selected_classifier_id: {type: Number, state: true},
        loading: {type: Boolean, state: true},
        run_results: {type: Object, state: true}
    };

    #currentRunFiles = new Map(); // Map of file ID -> file info

    constructor() {
        super();
        this.classifier_sets = [];
        this.current_classifier_set = null;
        this.current_classifier = null;
        this.selected_classifier_set_id = null;
        this.selected_classifier_id = null;
        this.loading = false;
        this.run_results = null;
    }

    static styles = css`
        .container {
            display: flex;
            gap: 20px;
            height: 90vh;
            padding: 10px;
            font-family: Arial, sans-serif;
            overflow: hidden;
        }
        
        .left-column {
            display: flex;
            flex-direction: column;
            max-width: 300px;
            gap: 20px;
            height: 100%;
            min-height: 0; /* Allow flex items to shrink */
        }
        
        .classifier-sets-panel,
        .classifiers-panel,
        .terms-panel,
        .results-panel {
            padding: 15px;
            display: flex;
            flex-direction: column;
            min-height: 0; /* Allow flex items to shrink */
            height: 100%;
        }
        
        .classifier-sets-panel,
        .classifiers-panel {
            flex: 1;
            min-height: 200px; /* Minimum height to ensure visibility */
        }
        
        .terms-panel,
        .results-panel {
            flex: 1;
            height: 100%;
        }
        
        .classifier-sets-list,
        .classifiers-list,
        .terms-list,
        .results-display {
            flex: 1;
            overflow-y: auto;
            min-height: 0; /* Allow scrolling */
        }
        
        .action-buttons {
            flex-shrink: 0; /* Prevent buttons from being squeezed */
            margin-top: 10px;
        }
        
        .panel-title {
            font-weight: bold;
            margin-bottom: 15px;
            font-size: 14px;
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
        
        .action-buttons {
            display: flex;
            gap: 5px;
            margin: 10px 0;
            flex-wrap: wrap;
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
        
        .term-row {
            position: relative;
            margin: 10px 0;
            padding: 10px;
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .term-delete-btn {
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
        
        .term-delete-btn:hover {
            background: #c82333;
        }
        
        .term-text-input {
            width: calc(100% - 35px);
            margin-bottom: 8px;
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 2px;
        }
        
        .term-controls {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        
        .term-control-group {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .term-control-label {
            font-size: 12px;
            color: #666;
            font-weight: bold;
        }
        
        .term-input {
            padding: 4px;
            border: 1px solid #ccc;
            border-radius: 2px;
        }
        
        .results-display {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        .file-result {
            margin-bottom: 20px;
            padding: 10px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        
        .file-result h4 {
            margin: 0 0 10px 0;
            color: #007bff;
            font-size: 16px;
        }
        
        .classification-item {
            padding: 4px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .classification-item:last-child {
            border-bottom: none;
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
            border: none;
            padding: 10px 20px;
            font-weight: bold;
            margin-top: 15px;
            flex-shrink: 0; /* Prevent button from being squeezed */
        }
        
        .run-button:hover {
            background: #218838;
        }
    `;

    server_interface(api) {
        this.init_server(api);
        
        // Load classifier sets list
        this.server.define_endpoint(
            "/classifiers",
            (resp) => {
                this.classifier_sets = resp;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_GET
        );
        
        // Load specific classifier set details
        this.server.define_endpoint(
            "/classifiers/{id}",
            (resp) => {
                this.current_classifier_set = resp;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_GET
        );
        
        // Save classifier set
        this.server.define_endpoint(
            "/classifiers/{id}",
            (resp) => {
                this.#load_classifier_sets();
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );
        
        // Run classifier against files
        this.server.define_endpoint(
            "/classifiers/run/{classifier_set_id}/{document_id}",
            (resp) => {
                // Handle multiple file results by accumulating them
                if (!this.run_results || this.run_results.loading) {
                    this.run_results = { files: [] };
                }
                
                // Extract document ID from the response
                const documentId = resp.document_id ? resp.document_id.toString() : null;
                
                // Get classification results (everything except document_id)
                const classificationResults = { ...resp };
                delete classificationResults.document_id;
                
                // Find the file info using the map
                const fileInfo = documentId ? this.#currentRunFiles.get(documentId) : null;
                
                if (!fileInfo) {
                    console.error("Cannot find file for document_id:", documentId);
                    return; // Skip this result if we can't match it
                }

                // Add new result
                this.run_results.files.push({
                    fileName: fileInfo.name,
                    fileId: fileInfo.id,
                    results: classificationResults
                });

                this.requestUpdate();
            },
            HTTP_GET
        );
    }

    login_success() {
        this.#load_classifier_sets();
    }

    #load_classifier_sets() {
        this.loading = true;
        this.server.call("/classifiers", HTTP_GET);
    }

    #load_classifier_set(classifier_set_id) {
        this.loading = true;
        this.selected_classifier_set_id = classifier_set_id;
        this.server.call("/classifiers/{id}", HTTP_GET, null, null, {id: classifier_set_id});
    }

    // UI event handlers
    #create_classifier_set_clicked(e) {
        const name = prompt("Enter classifier set name:");
        if (name) {
            const newSet = {
                id: 0,
                name: name,
                classifiers: []
            };
            this.server.call("/classifiers/{id}", HTTP_POST_JSON, newSet, null, {id: 0});
        }
    }

    #rename_classifier_set_clicked(e) {
        if (this.selected_classifier_set_id) {
            const currentName = this.classifier_sets.find(s => s.id === this.selected_classifier_set_id)?.name || "";
            const newName = prompt("Enter new classifier set name:", currentName);
            if (newName && newName !== currentName) {
                const updatedSet = {...this.current_classifier_set, name: newName};
                this.server.call("/classifiers/{id}", HTTP_POST_JSON, updatedSet, null, {id: this.selected_classifier_set_id});
            }
        }
    }

    #delete_classifier_set_clicked(e) {
        if (this.selected_classifier_set_id && confirm("Delete this classifier set?")) {
            // Implementation would depend on DELETE endpoint
            console.log("Delete classifier set", this.selected_classifier_set_id);
        }
    }

    #classifier_set_clicked(e) {
        const id = parseInt(e.target.dataset.classifierSetId);
        this.#load_classifier_set(id);
    }

    #classifier_clicked(e) {
        const id = parseInt(e.target.dataset.classifierId);
        this.selected_classifier_id = id;
        this.current_classifier = this.current_classifier_set?.classifiers?.find(c => c.id === id) || null;
        this.requestUpdate();
    }

    #create_classifier_clicked(e) {
        if (!this.current_classifier_set) return;
        
        const name = prompt("Enter classifier name:");
        if (name) {
            const newClassifier = {
                id: Date.now(), // temporary ID
                name: name,
                terms: []
            };
            
            const updatedSet = {
                ...this.current_classifier_set,
                classifiers: [...this.current_classifier_set.classifiers, newClassifier]
            };
            
            this.current_classifier_set = updatedSet;
            this.requestUpdate();
        }
    }

    #rename_classifier_clicked(e) {
        if (!this.current_classifier) return;
        
        const newName = prompt("Enter new classifier name:", this.current_classifier.name);
        if (newName && newName !== this.current_classifier.name) {
            this.current_classifier.name = newName;
            this.requestUpdate();
        }
    }

    #delete_classifier_clicked(e) {
        if (!this.current_classifier || !this.current_classifier_set) return;
        
        if (confirm("Delete this classifier?")) {
            const updatedClassifiers = this.current_classifier_set.classifiers.filter(
                c => c.id !== this.current_classifier.id
            );
            
            this.current_classifier_set = {
                ...this.current_classifier_set,
                classifiers: updatedClassifiers
            };
            
            this.current_classifier = null;
            this.selected_classifier_id = null;
            this.requestUpdate();
        }
    }

    #create_term_clicked(e) {
        if (!this.current_classifier) return;
        
        const term = prompt("Enter term:");
        const distance = parseInt(prompt("Enter distance (0-5):", "1"));
        const weight = parseFloat(prompt("Enter weight (0.0-1.0):", "1.0"));
        
        if (term) {
            const newTerm = { term, distance: distance || 1, weight: weight || 1.0 };
            this.current_classifier.terms = [...this.current_classifier.terms, newTerm];
            this.requestUpdate();
        }
    }

    #delete_term_clicked(e) {
        if (!this.current_classifier) return;
        
        const termIndex = parseInt(e.target.dataset.termIndex);
        this.current_classifier.terms = this.current_classifier.terms.filter((_, index) => index !== termIndex);
        this.requestUpdate();
    }

    #term_changed(e) {
        if (!this.current_classifier) return;
        
        const termIndex = parseInt(e.target.dataset.termIndex);
        const field = e.target.dataset.field;
        const value = e.target.value;
        
        if (field === 'distance') {
            this.current_classifier.terms[termIndex].distance = parseInt(value);
        } else if (field === 'weight') {
            this.current_classifier.terms[termIndex].weight = parseFloat(value);
        } else if (field === 'term') {
            this.current_classifier.terms[termIndex].term = value;
        }
        
        this.requestUpdate();
    }

    #save_clicked(e) {
        if (this.current_classifier_set && this.selected_classifier_set_id) {
            this.server.call("/classifiers/{id}", HTTP_POST_JSON, this.current_classifier_set, null, {id: this.selected_classifier_set_id});
        }
    }

    async #run_against_files_clicked(e) {
        if (!this.selected_classifier_set_id) {
            alert("Please select a classifier set first");
            return;
        }
        
        try {
            const selectedFilesResult = await multicall({
                target: "get_selected_files",
                query: "[jsum='files_list']",
                params: []
            });
            
            // multicall returns an array of result objects with 'results' property
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
            this.#currentRunFiles.clear(); // Reset the file tracking map
            this.requestUpdate();
            
            // Store file information for display using ID as key
            selectedFiles.forEach(file => {
                this.#currentRunFiles.set(file.id.toString(), file);
            });
            
            // Run classification against all selected files in parallel
            // The API will handle multiple calls to the same endpoint automatically
            // The callback will use document_id from the response to match results to files
            selectedFiles.forEach(file => {
                this.server.call("/classifiers/run/{classifier_set_id}/{document_id}", HTTP_GET, null, null, {
                    classifier_set_id: this.selected_classifier_set_id,
                    document_id: file.id
                });
            });
            
        } catch (error) {
            console.error("Error running classifier:", error);
            this.run_results = { error: "Error running classifier against files" };
            this.requestUpdate();
        }
    }

    render() {
        return html`
            <div class="container">
                <!-- Left Column: Classifier Sets and Classifiers stacked -->
                <div class="left-column">
                    <!-- Classifier Sets Panel -->
                    <div class="classifier-sets-panel">
                        <h3>Classifier Sets</h3>
                        
                        ${this.loading ? html`<div class="loading">Loading...</div>` : ''}
                        
                        <div class="classifier-sets-list">
                            ${this.classifier_sets.map(set => html`
                                <div 
                                    class="list-item ${this.selected_classifier_set_id === set.id ? 'selected' : ''}"
                                    data-classifier-set-id=${set.id}
                                    @click=${this.#classifier_set_clicked}
                                >
                                    ${set.name}
                                </div>
                            `)}
                        </div>
                        
                        <div class="action-buttons">
                            <button class="btn btn-primary" @click=${this.#create_classifier_set_clicked}>Create new ClassifierSet</button>
                            <button class="btn" @click=${this.#rename_classifier_set_clicked} ?disabled=${!this.selected_classifier_set_id}>Rename</button>
                            <button class="btn btn-danger" @click=${this.#delete_classifier_set_clicked} ?disabled=${!this.selected_classifier_set_id}>Delete</button>
                        </div>
                    </div>

                    <!-- Classifiers Panel -->
                    <div class="classifiers-panel">
                        <h3>Classifiers</h3>
                        
                        ${!this.current_classifier_set ? 
                            html`<div class="no-selection">Select a classifier set to view classifiers</div>` :
                            html`
                                <div class="classifiers-list">
                                    ${this.current_classifier_set.classifiers?.map(classifier => html`
                                        <div 
                                            class="list-item ${this.selected_classifier_id === classifier.id ? 'selected' : ''}"
                                            data-classifier-id=${classifier.id}
                                            @click=${this.#classifier_clicked}
                                        >
                                            ${classifier.name}
                                        </div>
                                    `) || ''}
                                </div>
                            `
                        }
                        
                        <div class="action-buttons">
                            <button class="btn btn-primary" @click=${this.#create_classifier_clicked} ?disabled=${!this.current_classifier_set}>New</button>
                            <button class="btn" @click=${this.#rename_classifier_clicked} ?disabled=${!this.current_classifier}>Rename</button>
                            <button class="btn btn-danger" @click=${this.#delete_classifier_clicked} ?disabled=${!this.current_classifier}>Delete</button>
                            <button class="btn" @click=${this.#save_clicked} ?disabled=${!this.current_classifier_set}>Save</button>
                        </div>
                    </div>
                </div>

                <!-- Terms Panel -->
                <div class="terms-panel">
                    <h3>Terms</h3>
                    
                    ${!this.current_classifier ? 
                        html`<div class="no-selection">Select a classifier to view terms</div>` :
                        html`
                            <div class="terms-list">
                                ${this.current_classifier.terms?.map((term, index) => html`
                                    <div class="term-row">
                                        <button 
                                            class="term-delete-btn" 
                                            data-term-index=${index}
                                            @click=${this.#delete_term_clicked}
                                            title="Delete term"
                                        >✕</button>
                                        
                                        <input 
                                            type="text" 
                                            class="term-text-input" 
                                            .value=${term.term}
                                            data-term-index=${index}
                                            data-field="term"
                                            @input=${this.#term_changed}
                                            placeholder="Enter term text..."
                                        />
                                        
                                        <div class="term-controls">
                                            <div class="term-control-group">
                                                <label class="term-control-label">Distance</label>
                                                <input 
                                                    type="number" 
                                                    class="term-input" 
                                                    .value=${term.distance}
                                                    data-term-index=${index}
                                                    data-field="distance"
                                                    @input=${this.#term_changed}
                                                    min="0" max="10"
                                                />
                                            </div>
                                            
                                            <div class="term-control-group">
                                                <label class="term-control-label">Weight</label>
                                                <input 
                                                    type="number" 
                                                    class="term-input" 
                                                    .value=${term.weight}
                                                    data-term-index=${index}
                                                    data-field="weight"
                                                    @input=${this.#term_changed}
                                                    min="0" max="1" step="0.1"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                `) || ''}
                            </div>
                            
                            <div class="action-buttons">
                                <button class="btn btn-primary" @click=${this.#create_term_clicked} ?disabled=${!this.current_classifier}>Create a new Term</button>
                            </div>
                        `
                    }
                </div>

                <!-- Results Panel -->
                <div class="results-panel">
                    <h3>Classification Results</h3>
                    
                    <button class="btn run-button" @click=${this.#run_against_files_clicked} ?disabled=${!this.selected_classifier_set_id}>Run against selected files</button>
                    
                    ${this.run_results && !this.run_results.loading ? 
                        html`
                            <div class="results-display">
                                ${this.run_results.files ? 
                                    // Multiple file results
                                    this.run_results.files.map((fileResult, index) => html`
                                        <div class="file-result">
                                            <h4>${fileResult.fileName} Results:</h4>
                                            ${Object.entries(fileResult.results).map(([classifier, score]) => html`
                                                <div class="classification-item"><strong>${classifier}:</strong> ${score}</div>
                                            `)}
                                        </div>
                                    `) :
                                    // Single result format (fallback)
                                    html`
                                        <h4>Classification Results:</h4>
                                        ${Object.entries(this.run_results).map(([classifier, score]) => html`
                                            <div class="classification-item"><strong>${classifier}:</strong> ${score}</div>
                                        `)}
                                    `
                                }
                            </div>
                        ` :
                        this.run_results && this.run_results.loading ?
                        html`<div class="results-display loading">Running classification...</div>` :
                        html`<div class="results-display no-selection">Run a classifier to see results here</div>`
                    }
                </div>
            </div>
        `;
    }
}

customElements.define('classifier-editor', ClassifierEditor);