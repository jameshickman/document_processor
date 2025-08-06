import {LitElement} from '../../node_modules/@lit';
import {API_REST} from './API.js';
import {bearer_handler} from './jwt_relay.js';

/**
 * Base Class that extends Lit
 * and adds the server interface handling.
 */

export class BaseComponent extends LitElement {
    server = null;
    files_service_domain = '';
    origin_domain = '';
    generate_jwt_route = '';
    server_error_handel = (err) => {
        console.log("Server communication error: " + err);
    };

    /**
     * Initialize the server interface.
     * If the instance of API_REST is created externally, pass it in.
     * Otherwise, create the server interface.
     *
     * Must be called before the widget is useable and can connect to the remote server.
     *
     * @param serverAPI Optional instance of API_REST
     * @returns API_REST instance
     */
    init_server(serverAPI) {
        if (serverAPI !== undefined && serverAPI instanceof API_REST) {
            this.server = serverAPI;
        }
        else {
            if (this.files_service_domain === '' || this.origin_domain === '' || this.generate_jwt_route === '') {
                throw new Error("Missing server init values");
            }
            this.server = new API_REST(this.files_service_domain, this.server_error_handel.bind(this));
            this.server.set_reauthorize(
                bearer_handler(
                    this.origin_domain,
                    this.generate_jwt_route
                )
            );
        }
        this.server_operations_setup();
        return this.server;
    }

    get_server_instance() {
        return this.server;
    }

    connectedCallback() {
        this.connect_event_handlers();
    };

    /**
     * Override with method to set up server operations
     */
    server_operations_setup() {};

    connect_event_handlers() {};
}