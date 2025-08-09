class NavigationView extends HTMLElement {
    #views;
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
            <div class='view_container'>
                <slot></slot>
            </div>
        `;
    }

    connectedCallback() {
        this.#views = {};
        let first_view = false;
        let default_view = false;
        for (let el_view of this.children) {
            const view_name = el_view.dataset.name;
            if (first_view === false) first_view = view_name;
            if (el_view.dataset.hasOwnProperty('default')) default_view = view_name;
            if (this.#views.hasOwnProperty(view_name) || view_name === undefined) {
                throw new Error('A view must define a unique value for the data-name property');
            }
            this.#views[view_name] = el_view;
        }
        if (window.hasOwnProperty('persist') && this.id !== undefined) {
            window.persist.register(this.id, (values) => {
                if ('view' in values) {
                    this.#goto_view(values['view']);
                }
                else {
                    if (default_view !== false) {
                        this.#goto_view(default_view);
                    }
                    else if (first_view !== false) {
                        this.#goto_view(first_view);
                    }
                }
            });
        }
        if (default_view !== false) {
            this.#goto_view(default_view);
        }
        else if (first_view !== false) {
            this.#goto_view(first_view);
        }
    }

    #goto_view(view_to_show) {
        for (const view_name in this.#views) {
            if (view_name === view_to_show) {
                this.#views[view_name].style.display = 'block';
            }
            else {
                this.#views[view_name].style.display = 'none';
            }
        }
    }

    async goto_view(view_to_show) {
        this.#goto_view(view_to_show);
        if (window.hasOwnProperty('persist') && this.id !== undefined) {
            window.persist.set(this.id, {
                view: view_to_show
            });
        }
    }
}

customElements.define('navigation-views', NavigationView);

export {NavigationView};