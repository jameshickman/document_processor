import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";

export class ExtractorEditor extends BaseComponent {
    static properties = {};
    static styles = css``;

    constructor() {
        super();
    }

    server_interface(api) {
        this.init_server(api);

    }

    render() {
        return html``;
    }
}

customElements.define('extractor-editor', ExtractorEditor);