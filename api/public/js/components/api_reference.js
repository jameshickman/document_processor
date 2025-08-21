import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET } from "../lib/API.js";
import {html, css} from "lit";

/*
 * Component to display the names and IDs of the classifiers and extractors.
 * Note that no call needs to be made to the server to get this information
 * as this will be listening for the REST calls invoked in the editor components.
 */

class ApiReference extends BaseComponent {
    static styles = css`
        .reference-container {
            width: 100%;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .tables-wrapper {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .table-section {
            flex: 1;
            min-width: 300px;
        }
        
        .reference-table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .reference-table th,
        .reference-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        .reference-table th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        
        .reference-table tbody tr:hover {
            background-color: #f8f9fa;
        }
        
        .id-column {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #007bff;
            width: 60px;
        }
        
        .name-column {
            word-break: break-word;
        }
        
        .no-data {
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 20px;
        }
        
        .section-title {
            margin: 0 0 15px 0;
            color: #495057;
            font-size: 18px;
            font-weight: 600;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #6c757d;
        }
        
        .error-message {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            text-align: center;
        }
        
        .refresh-button {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin: 10px 0;
        }
        
        .refresh-button:hover {
            background: #0056b3;
        }
        
        .refresh-button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
    `;

    static properties = {
        classifiers: { type: Array },
        extractors: { type: Array },
        loading: { type: Boolean },
        error: { type: String }
    };

    constructor() {
        super();
        this.classifiers = [];
        this.extractors = [];
        this.loading = false;
        this.error = '';
    }

    connectedCallback() {
        super.connectedCallback();
    }

    server_interface(api) {
        this.init_server(api);

        this.server.define_endpoint(
            "/classifiers",
            (resp) => {
                this.handleClassifiersResponse(resp);
            },
            HTTP_GET
        );

        this.server.define_endpoint(
            "/extractors",
            (resp) => {
                this.handleExtractorsResponse(resp);
            },
            HTTP_GET
        );
    }

    handleClassifiersResponse(resp) {
        if (resp && Array.isArray(resp)) {
            this.classifiers = resp.map(item => ({
                id: item.id,
                name: item.name || `Classifier ${item.id}`
            }));
        } else if (resp && resp.classifiers && Array.isArray(resp.classifiers)) {
            this.classifiers = resp.classifiers.map(item => ({
                id: item.id,
                name: item.name || `Classifier ${item.id}`
            }));
        } else {
            console.warn('Unexpected classifiers response format:', resp);
            this.classifiers = [];
        }
        this.requestUpdate();
    }

    handleExtractorsResponse(resp) {
        if (resp && Array.isArray(resp)) {
            this.extractors = resp.map(item => ({
                id: item.id,
                name: item.name || `Extractor ${item.id}`
            }));
        } else if (resp && resp.extractors && Array.isArray(resp.extractors)) {
            this.extractors = resp.extractors.map(item => ({
                id: item.id,
                name: item.name || `Extractor ${item.id}`
            }));
        } else {
            console.warn('Unexpected extractors response format:', resp);
            this.extractors = [];
        }
        this.requestUpdate();
    }


    renderTable(title, data, emptyMessage) {
        return html`
            <div class="table-section">
                <h3 class="section-title">${title}</h3>
                <table class="reference-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length > 0 ? data.map(item => html`
                            <tr>
                                <td class="id-column">${item.id}</td>
                                <td class="name-column">${item.name}</td>
                            </tr>
                        `) : html`
                            <tr>
                                <td colspan="2" class="no-data">${emptyMessage}</td>
                            </tr>
                        `}
                    </tbody>
                </table>
            </div>
        `;
    }

    render() {
        if (this.loading) {
            return html`
                <div class="reference-container">
                    <div class="loading">Loading reference data...</div>
                </div>
            `;
        }

        if (this.error) {
            return html`
                <div class="reference-container">
                    <div class="error-message">
                        ${this.error}
                    </div>
                    <button 
                        class="refresh-button" 
                        @click=${this.refreshData}
                        ?disabled=${this.loading}>
                        Retry
                    </button>
                </div>
            `;
        }

        return html`
            <div class="reference-container">
                <div class="tables-wrapper">
                    ${this.renderTable(
                        'Classifiers', 
                        this.classifiers, 
                        'No classifiers available'
                    )}
                    ${this.renderTable(
                        'Extractors', 
                        this.extractors, 
                        'No extractors available'
                    )}
                </div>
            </div>
        `;
    }
}

customElements.define('api-reference', ApiReference);