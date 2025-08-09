import {multicall} from "../lib/jsum.js";

class NavigationMenu extends HTMLElement {
    #navigation_control;
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
            <slot></slot>
        `;
    }

    connectedCallback() {
        this.#navigation_control = this.dataset.target;
        for (const el_item of this.children) {
            el_item.addEventListener('click', (e) => {
                const view_name = e.currentTarget.dataset.view;
                multicall({
                    'target': 'goto_view',
                    'query': this.#navigation_control,
                    'params': [view_name]
                });
            });
        }
    }
}

customElements.define('navigation-menu', NavigationMenu);

export {NavigationMenu};