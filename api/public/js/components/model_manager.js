import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON, HTTP_DELETE } from "../lib/API.js";
import {html, css} from "lit";


export class ModelManager extends BaseComponent {
    static properties = {
        models: {type: Array, state: true},
        current_model: {type: Object, state: true},
        selected_model_id: {type: Number, state: true},
        loading: {type: Boolean, state: true},
        creating_new: {type: Boolean, state: true},
        new_model_name: {type: String, state: true}
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

        .right-column {
            flex: 1;
            max-width: 600px;
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

        .models-list {
            flex: 1;
            overflow-y: auto;
            min-height: 0;
            margin-bottom: 10px;
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

        .btn-danger:hover {
            background: #c82333;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .field-label {
            font-size: 13px;
            font-weight: 600;
            color: #555;
            margin-bottom: 5px;
            display: block;
        }

        input, select, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 14px;
            font-family: inherit;
            box-sizing: border-box;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #007bff;
        }

        .editor-content {
            flex: 1;
            overflow-y: auto;
            min-height: 0;
        }

        .no-selection {
            text-align: center;
            color: #999;
            padding: 40px;
            font-size: 16px;
        }

        .create-new-input {
            padding: 8px;
            margin-bottom: 10px;
            width: 100%;
            border: 2px solid #007bff;
            border-radius: 3px;
            font-size: 14px;
            box-sizing: border-box;
        }

        .help-text {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            font-style: italic;
        }
    `;

    constructor() {
        super();
        this.models = [];
        this.current_model = null;
        this.selected_model_id = null;
        this.loading = false;
        this.creating_new = false;
        this.new_model_name = '';
    }

    server_interface(api) {
        this.init_server(api);

        this.server.define_endpoint("/llm_models",
            (resp) => {
                this.models = resp;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_GET
        );

        this.server.define_endpoint("/llm_models/{id}",
            (resp) => {
                this.current_model = resp;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_GET
        );

        this.server.define_endpoint("/llm_models/{id}",
            (resp) => {
                this.creating_new = false;
                this.new_model_name = '';
                this.#load_models();
                if (resp.id) {
                    this.#load_model(resp.id);
                }
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint("/llm_models/{id}",
            (resp) => {
                this.current_model = null;
                this.selected_model_id = null;
                this.#load_models();
                this.requestUpdate();
            },
            HTTP_DELETE
        );
    }

    login_success() {
        this.#load_models();
    }

    #load_models() {
        this.loading = true;
        this.server.call("/llm_models", HTTP_GET);
    }

    #load_model(model_id) {
        this.selected_model_id = model_id;
        this.loading = true;
        this.server.call("/llm_models/{id}", HTTP_GET, null, null, {id: model_id});
    }

    #model_clicked(model) {
        if (this.creating_new) {
            return;
        }
        this.#load_model(model.id);
    }

    #create_model_clicked() {
        this.creating_new = true;
        this.new_model_name = '';
        this.current_model = null;
        this.selected_model_id = null;
        this.requestUpdate();
    }

    #cancel_create_clicked() {
        this.creating_new = false;
        this.new_model_name = '';
        this.requestUpdate();
    }

    #new_name_keypress(e) {
        if (e.key === 'Enter') {
            this.#confirm_create_clicked();
        } else if (e.key === 'Escape') {
            this.#cancel_create_clicked();
        }
    }

    #confirm_create_clicked() {
        if (!this.new_model_name || !this.new_model_name.trim()) {
            alert('Please enter a model name');
            return;
        }

        const new_model_data = {
            name: this.new_model_name.trim(),
            provider: 'openai',
            model_identifier: 'gpt-3.5-turbo',
            base_url: null,
            temperature: 0.0,
            max_tokens: 2048,
            timeout: 360,
            model_kwargs_json: null
        };

        this.server.call("/llm_models/{id}", HTTP_POST_JSON, new_model_data, null, {id: 0});
    }

    #save_model_clicked() {
        if (!this.current_model) return;

        if (!this.current_model.name || !this.current_model.name.trim()) {
            alert('Model name cannot be empty');
            return;
        }

        if (!this.current_model.provider) {
            alert('Please select a provider');
            return;
        }

        if (!this.current_model.model_identifier || !this.current_model.model_identifier.trim()) {
            alert('Model identifier cannot be empty');
            return;
        }

        this.server.call("/llm_models/{id}", HTTP_POST_JSON, this.current_model, null, {id: this.current_model.id});
    }

    #delete_model_clicked() {
        if (!this.current_model) return;

        if (confirm(`Are you sure you want to delete the model "${this.current_model.name}"?`)) {
            this.server.call("/llm_models/{id}", HTTP_DELETE, null, null, {id: this.current_model.id});
        }
    }

    #field_changed(field, e) {
        if (this.current_model) {
            this.current_model[field] = e.target.value;
            this.requestUpdate();
        }
    }

    #number_field_changed(field, e) {
        if (this.current_model) {
            const value = parseFloat(e.target.value);
            if (!isNaN(value)) {
                this.current_model[field] = value;
                this.requestUpdate();
            }
        }
    }

    render() {
        return html`
            <div class="container">
                <div class="left-column">
                    <div class="panel">
                        <h3>LLM Models</h3>

                        ${this.creating_new ? html`
                            <input
                                type="text"
                                class="create-new-input"
                                placeholder="Enter model name..."
                                .value=${this.new_model_name}
                                @input=${(e) => this.new_model_name = e.target.value}
                                @keydown=${this.#new_name_keypress}
                                autofocus
                            />
                            <div class="action-buttons">
                                <button class="btn btn-primary" @click=${this.#confirm_create_clicked}>Create</button>
                                <button class="btn" @click=${this.#cancel_create_clicked}>Cancel</button>
                            </div>
                        ` : ''}

                        <div class="models-list">
                            ${this.models.map(model => html`
                                <div
                                    class="list-item ${this.selected_model_id === model.id ? 'selected' : ''}"
                                    @click=${() => this.#model_clicked(model)}
                                >
                                    ${model.name}
                                </div>
                            `)}
                        </div>

                        ${!this.creating_new ? html`
                            <div class="action-buttons">
                                <button class="btn btn-primary" @click=${this.#create_model_clicked}>Create New</button>
                                <button class="btn btn-danger" @click=${this.#delete_model_clicked} ?disabled=${!this.current_model}>Delete</button>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="right-column">
                    <div class="panel">
                        ${!this.current_model ? html`
                            <div class="no-selection">Select a model to edit or create a new one</div>
                        ` : html`
                            <h3>Model Configuration</h3>
                            <div class="editor-content">
                                <div class="form-group">
                                    <label class="field-label">Name:</label>
                                    <input
                                        type="text"
                                        .value=${this.current_model.name || ''}
                                        @input=${(e) => this.#field_changed('name', e)}
                                        placeholder="e.g., GPT-4 Turbo, Claude Sonnet"
                                    />
                                    <div class="help-text">Display name for this model</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Provider:</label>
                                    <select
                                        .value=${this.current_model.provider || 'openai'}
                                        @change=${(e) => this.#field_changed('provider', e)}
                                    >
                                        <option value="openai">OpenAI</option>
                                        <option value="deepinfra">DeepInfra</option>
                                        <option value="ollama">Ollama</option>
                                    </select>
                                    <div class="help-text">LLM provider service</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Model Identifier:</label>
                                    <input
                                        type="text"
                                        .value=${this.current_model.model_identifier || ''}
                                        @input=${(e) => this.#field_changed('model_identifier', e)}
                                        placeholder="e.g., gpt-4, meta-llama/Llama-3-70b"
                                    />
                                    <div class="help-text">Actual model name used by the API</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Base URL (Optional):</label>
                                    <input
                                        type="text"
                                        .value=${this.current_model.base_url || ''}
                                        @input=${(e) => this.#field_changed('base_url', e)}
                                        placeholder="Leave empty for default"
                                    />
                                    <div class="help-text">Custom API endpoint (leave empty to use default)</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Temperature:</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        min="0"
                                        max="2"
                                        .value=${this.current_model.temperature ?? 0.0}
                                        @input=${(e) => this.#number_field_changed('temperature', e)}
                                    />
                                    <div class="help-text">Randomness in output (0 = deterministic, 2 = very random)</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Max Tokens:</label>
                                    <input
                                        type="number"
                                        step="1"
                                        min="1"
                                        .value=${this.current_model.max_tokens ?? 2048}
                                        @input=${(e) => this.#number_field_changed('max_tokens', e)}
                                    />
                                    <div class="help-text">Maximum length of generated response</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Timeout (seconds):</label>
                                    <input
                                        type="number"
                                        step="1"
                                        min="1"
                                        .value=${this.current_model.timeout ?? 360}
                                        @input=${(e) => this.#number_field_changed('timeout', e)}
                                    />
                                    <div class="help-text">Request timeout in seconds</div>
                                </div>

                                <div class="form-group">
                                    <label class="field-label">Model Kwargs (JSON, Optional):</label>
                                    <textarea
                                        rows="3"
                                        .value=${this.current_model.model_kwargs_json || ''}
                                        @input=${(e) => this.#field_changed('model_kwargs_json', e)}
                                        placeholder='{"top_p": 0.9, "frequency_penalty": 0.0}'
                                    ></textarea>
                                    <div class="help-text">Additional provider-specific parameters as JSON</div>
                                </div>

                                <div class="action-buttons">
                                    <button class="btn btn-primary" @click=${this.#save_model_clicked}>Save Model</button>
                                </div>
                            </div>
                        `}
                    </div>
                </div>
            </div>
        `;
    }
}

customElements.define('model-manager', ModelManager);
