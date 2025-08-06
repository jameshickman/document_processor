import { API_REST, HTTP_GET } from "./API.js";

/**
 * Return a handler to recreate the Bearer token from the local system and update the API
 * Model.
 *
 *
 * @returns {CallableFunction} Handler to start the Bearer token recreation process
 * @param local_domain
 * @param local_system_end_point
 */
export function bearer_handler(local_domain, local_system_end_point) {
    let remote_api = null;
    const api = new API_REST(local_domain, (err) => {
        console.log("Problem generating a JWT Token: " + err)
    });
    api.define_endpoint(local_system_end_point, (payload) => {
        remote_api.set_bearer_token(payload.access_token);
        remote_api.recall();
    }, HTTP_GET);

    /**
     * Curry the state for accessing the local system
     * and return a function to register with the API
     */
    return (remote_api_instance, response) => {
        remote_api = remote_api_instance;
        api.call(local_system_end_point);
    };
}