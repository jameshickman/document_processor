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
        
        // Set first tab as active by default
        if (this.children.length > 0) {
            this.children[0].classList.add('active');
        }
        
        for (const el_item of this.children) {
            el_item.addEventListener('click', (e) => {
                // Remove active class from all tabs
                for (const tab of this.children) {
                    tab.classList.remove('active');
                }
                
                // Add active class to clicked tab
                e.currentTarget.classList.add('active');
                
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