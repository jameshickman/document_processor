import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";


export class ClassifierEditor extends BaseComponent {
    constructor() {
        super();
        this.form_elements = [];
    }

    #current_classifier_set_id = 0;

    static propTypes = {
        form_elements: {type: Array, state: true, required: true},
        extractor_set_list: {type: Array, state: true, required: true},
        terms_list: {type: Array, state: true, required: true},
    };

    static styles = css``;

    server_interface(api) {
        this.init_server(api);
        this.server.define_endpoint(
            "/classifiers",
            (resp) => {
                this.extractor_set_list.value = resp;
                this.requestUpdate();
            },
            HTTP_GET
        );
        this.server.define_endpoint(
            "/classifiers/",
            (resp) => {

            },
            HTTP_GET
        );
    }

    login_success() {
        this.#load_classifier_sets();
    }

    #load_classifier_sets() {
        this.server.call("/classifiers", HTTP_GET);
    }

    #load_classifier(classifier_id) {
        this.server.call(
            "/classifiers/",
            HTTP_POST_JSON,
            {
                classifier_set_id: classifier_id,
            });
    }

    // UI event handlers
    #add_button_clicked(e) {
    }

    #rename_selected_classifier_set(e) {
    }

    #classifier_clicked(e) {
        const id = e.target.dataset.id;
        this.#load_classifier(id);
    }

    render() {
        return html`
            <div class="container">
                <div class="classifier-set-list-container">
                    <ul id="classifier-set-list">
                        ${this.extractor_set_list.map(extractor => html`
                            <li 
                                    id="extractor-${extractor.id}"
                                    data-extractor-id=${extractor.id}
                                    @click=${this.#classifier_clicked}
                            >${extractor.name}</li>
                        `)}
                    </ul>
                    <div class="classifier-set-action-buttons">
                        <button 
                                id="add-classifier-set-btn" type="button" 
                                class="btn btn-sm btn-primary"
                                @click=${this.#add_button_clicked}
                        >Create Classifier</button>
                        <button
                            id="rename-classifier-set"
                            class="btn btn-sm btn-primary"
                    </div>
                </div>
                <div class="classifier-editor-container">
                    <form id="classifier-editor">
                        <div class="form-group">
                            <label for="classifier-name">Classifier Name</label>
                            <input type="text" class="form-control" id="classifier-name" placeholder="Enter classifier name"></input>
                        </div>
                        <div class="classifiers-container">
                            ${this.form_elements.map(form_element => html`
                            
                            `)}
                        </div>
                        <div class="buttons-container">
                            <button type="submit" id="save-classifier" class="btn btn-primary">Save</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }
}

customElements.define('classifier_editor', ClassifierEditor);