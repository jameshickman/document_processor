/*
 * Generic REST API call interface with deduplication and multiple call-back support.
 * (c) 2024 James Hickman <jamesATjameshickmanDOTnet>
 * MIT License
 * 
 * 2025-06-05:
 * Added support for Bearer Token. Typically, an encrypted JWT.
 *      If cb_revalidate set, call that on an authentication error.
 */

const HTTP_GET = 'get';
const HTTP_POST_FORM = 'post_form';
const HTTP_POST_JSON = 'post_json';
const HTTP_PUT = 'put';
const HTTP_DELETE = 'delete';

const cyrb53 = (str, seed = 0) => {
    let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;
    for(let i = 0, ch; i < str.length; i++) {
        ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1  = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2  = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  
    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
};

class API_REST {
    #host_url = '';
    #operations = {};
    #in_flight = {};
    #error_handler = null;
    #bearer_token = null;
    #cb_revalidate = null;
    #call_cache = [];
    #auth_active = false;
    #auth_retry_count = 0;
    #max_auth_retries = 3;
    #is_refreshing_auth = false;
    #pending_retries = 0;

    /**
     * 
     * @param {string} host_url              Base URL, if not provided defaults to '/'
     * @param {CallableFunction} cb_error    Call-back function on an error condition, if not provided error written to console.log()
     */
    constructor(host_url, cb_error) {
        if (host_url === undefined) {
            this.#host_url = '/';
        }
        else {
            this.#host_url = host_url;
        }
        if (cb_error === undefined) {
            this.#error_handler = (err) => {
                console.log(err);
            }
        }
        else {
            this.#error_handler = cb_error;
        }
    }

    /**
     * Set Bearer token
     *
     * @param token
     */
    set_bearer_token(token) {
        this.#bearer_token = token;
        this.#auth_active = true;
    }

    /**
     * Set the reauthorize function
     * 
     * @param {CallableFunction} f
     */
    set_reauthorize(f) {
        this.#cb_revalidate = f;
        this.#auth_active = true;
    } 

    /**
     * Define an end-point by its path and HTTP verb type
     * 
     * @param {string} signature            URL route signature, including {callouts}.
     * @param {CallableFunction} callback   Function to call back with value from server
     * @param {string} http_verb            Use constants for the request verb.
     * @returns {this}
     */
    define_endpoint(signature, callback, http_verb) {
        if (http_verb === undefined) http_verb = HTTP_GET;
        const key = http_verb + '|' + signature;
        if (!this.#operations.hasOwnProperty(key)) {
            this.#operations[key] = [callback];
        }
        else {
            this.#operations[key].push(callback);
        }
        return this;
    }

    /**
     * Clear authentication state and cache
     */
    #clear_auth_state() {
        this.#auth_retry_count = 0;
        this.#is_refreshing_auth = false;
        this.#call_cache = [];
        this.#bearer_token = null;
        this.#pending_retries = 0;
    }

    /**
     * Add call to cache with deduplication
     */
    #cache_failed_call(call_params) {
        const cache_key = this.#generate_cache_key(call_params);
        const existing = this.#call_cache.find(cached => this.#generate_cache_key(cached) === cache_key);
        if (!existing) {
            this.#call_cache.push(call_params);
        }
    }

    /**
     * Generate unique key for call caching
     */
    #generate_cache_key(call_params) {
        const {signature, http_verb, data, headers, path_vars} = call_params;
        return cyrb53(signature + http_verb + JSON.stringify(data) + JSON.stringify(headers) + JSON.stringify(path_vars));
    }

    /**
     * Re-run a call, the previous is cached,
     * Used for repeating a call after a failed authentication and the token recreated.
     * A brief delay to be sure all pending processes complete.
     */
    recall() {
        if (this.#call_cache.length === 0) {
            this.#is_refreshing_auth = false;
            return;
        }
        
        setTimeout(()=>{
            const cached_calls = [...this.#call_cache]; // Copy the cache
            this.#call_cache = []; // Clear cache before retrying
            this.#pending_retries = cached_calls.length;
            
            for (const call_params of cached_calls) {
                const {signature, http_verb, data, headers, path_vars} = call_params;
                this.call(
                    signature,
                    http_verb,
                    data,
                    headers,
                    path_vars,
                    true // Mark as retry
                );
            }
            
            // Fallback: if no cached calls, reset state immediately
            if (cached_calls.length === 0) {
                this.#is_refreshing_auth = false;
                this.#pending_retries = 0;
            }
        }, 500);
    }

    /**
     * Do a call to a defined endpoint. If an identical request in process, abort the duplicate.
     * If the end point has not been defined throw an exception.
     * 
     * @param {string} signature        URL route signature, including {callouts}.
     * @param {string} http_verb        Use constants for the request verb.
     * @param {object} data             Payload data.
     * @param {object} headers          Headers, key:value.
     * @param {object} path_vars        Values to inject into route.
     * @param {boolean} is_retry        Internal flag to prevent caching retry attempts.
     * @param {function} onProgress     Optional progress callback for HTTP_POST_FORM (percent, loaded, total).
     * @returns {boolean}               If initiating a network transaction, true.
     *                                  Else if an identical request in progress, false.
     */
    call(signature, http_verb, data, headers, path_vars, is_retry = false, onProgress = null) {
        if (http_verb === undefined) {
            http_verb = "get";
        }
        const signature_key = http_verb + '|' + signature;
        let url = signature;
        if (headers === undefined) {
            headers = {};
        }
        if (path_vars !== undefined) {
            url = this.#apply_path_values(signature, path_vars);
        }
        url = this.#host_url + url;
        
        if (this.#operations.hasOwnProperty(signature_key)) {
            const call_params = {
                signature, http_verb, data, headers, path_vars, signature_key, callbacks: this.#operations[signature_key]
            };
            
            switch(http_verb) {
                case HTTP_POST_FORM:
                    return this.#call_if_not_in_flight(signature_key, url, "POST", data, headers, true, call_params, is_retry, onProgress);
                case HTTP_POST_JSON:
                    return this.#call_if_not_in_flight(signature_key, url, "POST", data, headers, false, call_params, is_retry, undefined);
                case HTTP_DELETE:
                    return this.#call_if_not_in_flight(signature_key, url, "DELETE", null, headers, false, call_params, is_retry, undefined);
                case HTTP_PUT:
                    return this.#call_if_not_in_flight(signature_key, url, "PUT", data, headers, false, call_params, is_retry, undefined);
                default:
                    // HTTP_GET
                    return this.#call_if_not_in_flight(signature_key, url, "GET", null, headers, false, call_params, is_retry, undefined);
            }
        }
        throw new Error(signature_key + " has not been defined.");
    }

    #apply_path_values(path, data) {
        for (const n in data) {
            const token = "{" + n + "}";
            path = path.replace(token, data[n]);
        }
        return path;
    }

    #call_if_not_in_flight(signature, url, verb, data, headers, is_form, call_params, is_retry, onProgress) {
        if (!headers) headers = {};
        if (this.#auth_active) {
            headers['Authorization'] = "Bearer " + this.#bearer_token;
        }
        
        const fetch_wrapper = (callbacks_key) => {
            let resolved = false;
            return {
                resolved: () => {
                    return resolved;
                },
                launch: () => {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minuet timeout
                    
                    // Use XMLHttpRequest for form uploads with progress, otherwise use fetch
                    if (is_form && onProgress && typeof onProgress === 'function') {
                        this.#xhr_request(url, verb, data, headers, callbacks_key, onProgress, timeoutId, call_params, is_retry);
                        return; // XMLHttpRequest handles its own flow
                    }
                    
                    fetch(this.#build_request(url, verb, data, headers, is_form, controller.signal))
                    .then(async (response) => {
                        clearTimeout(timeoutId);
                        resolved = true;
                        
                        if (!response.ok) {
                            // Handle authentication errors properly
                            if (response.status === 401 && this.#cb_revalidate && !is_retry) {
                                if (this.#auth_retry_count < this.#max_auth_retries) {
                                    // Cache this specific failed request for retry (with deduplication)
                                    this.#cache_failed_call(call_params);
                                    
                                    // Only start auth refresh if not already in progress
                                    if (!this.#is_refreshing_auth) {
                                        this.#auth_retry_count++;
                                        this.#is_refreshing_auth = true;
                                        
                                        try {
                                            await this.#cb_revalidate(this, response);
                                            // Token refresh successful, retry will happen via recall()
                                        } catch (auth_error) {
                                            this.#clear_auth_state();
                                            this.#error_handler(auth_error);
                                        }
                                    }
                                    return;
                                } else {
                                    this.#clear_auth_state();
                                    this.#error_handler(new Error("Maximum authentication retries exceeded"));
                                    return;
                                }
                            }
                            
                            // Handle retry completion tracking on non-auth errors
                            if (is_retry) {
                                this.#pending_retries--;
                                if (this.#pending_retries <= 0) {
                                    this.#is_refreshing_auth = false;
                                    this.#pending_retries = 0;
                                }
                            }
                            
                            // Handle other HTTP errors
                            this.#error_handler(response);
                        }
                        else {
                            // Success - handle retry completion tracking
                            if (is_retry) {
                                this.#pending_retries--;
                                if (this.#pending_retries <= 0) {
                                    // All retries completed successfully
                                    this.#is_refreshing_auth = false;
                                    this.#auth_retry_count = 0;
                                    this.#pending_retries = 0;
                                }
                            } else if (!this.#is_refreshing_auth) {
                                // Regular successful call, reset retry count
                                this.#auth_retry_count = 0;
                            }
                            
                            try {
                                const payload = await response.json();
                                for (const cb of this.#operations[callbacks_key]) {
                                    cb(payload);
                                }
                            } catch (json_error) {
                                console.log(json_error);
                            }
                        }
                        this.#purge();
                    })
                    .catch((err) => {
                        clearTimeout(timeoutId);
                        resolved = true;
                        this.#purge();
                        
                        // Handle retry completion tracking on error
                        if (is_retry) {
                            this.#pending_retries--;
                            if (this.#pending_retries <= 0) {
                                this.#is_refreshing_auth = false;
                                this.#pending_retries = 0;
                            }
                        }
                        
                        if (err.name === 'AbortError') {
                            this.#error_handler(new Error("Request timeout"));
                        } else {
                            this.#error_handler(err);
                        }
                    })
                }
            }
        }

        const key = cyrb53(url + verb + JSON.stringify(data) + JSON.stringify(headers));
        if (this.#in_flight.hasOwnProperty(key)) {
            if (this.#in_flight[key].resolved()) {
                delete this.#in_flight[key];
            }
            else {
                return false;
            }
        }
        this.#in_flight[key] = fetch_wrapper(signature);
        this.#in_flight[key].launch();
        return true;
    }

    #xhr_request(url, verb, data, headers, callbacks_key, onProgress, timeoutId, call_params, is_retry) {
        const xhr = new XMLHttpRequest();
        
        // Set up progress tracking
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                onProgress(percentComplete, event.loaded, event.total);
            }
        });
        
        // Set up response handlers
        xhr.addEventListener('load', () => {
            clearTimeout(timeoutId);
            
            if (xhr.status >= 200 && xhr.status < 300) {
                // Success - handle retry completion tracking
                if (is_retry) {
                    this.#pending_retries--;
                    if (this.#pending_retries <= 0) {
                        // All retries completed successfully
                        this.#is_refreshing_auth = false;
                        this.#auth_retry_count = 0;
                        this.#pending_retries = 0;
                    }
                } else if (!this.#is_refreshing_auth) {
                    // Regular successful call, reset retry count
                    this.#auth_retry_count = 0;
                }
                
                try {
                    const payload = JSON.parse(xhr.responseText);
                    for (const cb of this.#operations[callbacks_key]) {
                        cb(payload);
                    }
                } catch (json_error) {
                    console.log(json_error);
                }
            } else if (xhr.status === 401 && this.#cb_revalidate && !is_retry) {
                // Handle authentication errors properly
                if (this.#auth_retry_count < this.#max_auth_retries) {
                    // Cache this specific failed request for retry (with deduplication)
                    this.#cache_failed_call(call_params);
                    
                    // Only start auth refresh if not already in progress
                    if (!this.#is_refreshing_auth) {
                        this.#auth_retry_count++;
                        this.#is_refreshing_auth = true;
                        
                        this.#cb_revalidate(this, {status: xhr.status, statusText: xhr.statusText})
                        .catch(auth_error => {
                            this.#clear_auth_state();
                            this.#error_handler(auth_error);
                        });
                    }
                    return;
                } else {
                    this.#clear_auth_state();
                    this.#error_handler(new Error("Maximum authentication retries exceeded"));
                    return;
                }
            } else {
                // Handle retry completion tracking on non-auth errors
                if (is_retry) {
                    this.#pending_retries--;
                    if (this.#pending_retries <= 0) {
                        this.#is_refreshing_auth = false;
                        this.#pending_retries = 0;
                    }
                }
                
                // Handle other HTTP errors
                this.#error_handler({status: xhr.status, statusText: xhr.statusText});
            }
            this.#purge();
        });
        
        xhr.addEventListener('error', () => {
            clearTimeout(timeoutId);
            this.#purge();
            
            // Handle retry completion tracking on error
            if (is_retry) {
                this.#pending_retries--;
                if (this.#pending_retries <= 0) {
                    this.#is_refreshing_auth = false;
                    this.#pending_retries = 0;
                }
            }
            
            this.#error_handler(new Error('Network error'));
        });
        
        xhr.addEventListener('abort', () => {
            clearTimeout(timeoutId);
            this.#purge();
            this.#error_handler(new Error("Request timeout"));
        });
        
        // Prepare form data
        const formData = new FormData();
        for (const key in data) {
            if (data[key] instanceof HTMLInputElement && data[key].type === 'file') {
                const fileInput = data[key];
                if (fileInput.files && fileInput.files.length > 0) {
                    for (let i = 0; i < fileInput.files.length; i++) {
                        formData.append(key, fileInput.files[i]);
                    }
                }
            } else {
                formData.append(key, data[key]);
            }
        }
        
        // Open request
        xhr.open(verb, url, true);
        
        // Set headers including Authorization if available
        for (const headerName in headers) {
            if (headerName.toLowerCase() !== 'content-type') {
                xhr.setRequestHeader(headerName, headers[headerName]);
            }
        }
        
        // Set timeout
        xhr.timeout = 30000;
        
        // Send request
        xhr.send(formData);
    }

    #build_request(url, verb, data, headers, is_form, signal) {
        if (!is_form && data) {
            headers['Content-Type'] = 'application/json';
        }
        const params = {
            method: verb,
            signal: signal // Add abort signal support
        };
        if (headers) {
            const h = new Headers();
            for (let k in headers) {
                h.set(k, headers[k]);
            }
            params['headers'] = h;
        }
        if (data) {
            if (is_form) {
        const fd = new FormData()
        for (const k in data) {
          if (data[k] instanceof HTMLInputElement && data[k].type === 'file') {
            const fileInput = data[k]
            if (fileInput.files && fileInput.files.length > 0) {
              for (let i = 0; i < fileInput.files.length; i++) {
                fd.append(k, fileInput.files[i])
              }
            }
          } else {
            fd.append(k, data[k])
          }
        }
        params.body = fd
            }
            else {
                params['body'] = JSON.stringify(data);
            }
        }
        return new Request(url, params);
    }

    #purge() {
        //console.log(this.#in_flight);
        for (const key in this.#in_flight) {
            if (this.#in_flight[key].resolved()) {
                delete this.#in_flight[key];
            }
        }
        //console.log(this.#in_flight);
    }


    /**
     * Download any file type with proper authentication and error handling.
     * 
     * This method handles authenticated downloads by automatically including
     * Authorization headers when available. It supports both direct URL downloads
     * and content-based downloads from API responses.
     * 
     * Features:
     * - Automatic Bearer token authentication
     * - Content-Disposition filename parsing with fallback
     * - Robust MIME type detection
     * - Error handling with optional callbacks
     * - Memory cleanup of blob URLs
     * - Cross-browser compatibility
     * 
     * @param {string} url - The URL to download from, or null if using content parameter
     * @param {string} content - Optional content to download as file (alternative to URL)
     * @param {string} defaultFilename - Default filename if Content-Disposition header not found
     * @param {string} mimeType - MIME type for the content (defaults to auto-detection)
     * @param {function} onSuccess - Optional success callback
     * @param {function} onError - Optional error callback
     * 
     * @example
     * // Download from URL (authenticated)
     * api.download('/api/classifiers/export/123');
     * 
     * @example
     * // Download content with custom filename
     * api.download(null, yamlContent, 'my-classifier.yaml', 'application/yaml');
     * 
     * @example
     * // Download with callbacks
     * api.download('/api/data/export', null, 'data.json', null, 
     *   () => console.log('Download started'),
     *   (error) => console.error('Download failed:', error)
     * );
     */
    download(url, content = null, defaultFilename = 'download', mimeType = null, onSuccess = null, onError = null) {
        try {
            if (url) {
                // URL-based download (authenticated)
                this.#downloadFromUrl(url, defaultFilename, onSuccess, onError);
            } else if (content) {
                // Content-based download
                this.#downloadFromContent(content, defaultFilename, mimeType, onSuccess, onError);
            } else {
                throw new Error('Either url or content must be provided');
            }
        } catch (error) {
            if (onError) {
                onError(error);
            } else {
                console.error('Download error:', error);
            }
        }
    }

    /**
     * Internal method to handle URL-based downloads with authentication
     * @private
     */
    #downloadFromUrl(url, defaultFilename, onSuccess, onError) {
        const params = {
            method: "GET"
        };
        
        if (this.#bearer_token !== null) {
            params['headers'] = {
                "Authorization": "Bearer " + this.#bearer_token
            };
        }
        
        const req = new Request(url, params);

        fetch(req)
            .then(result => {
                if (!result.ok) {
                    throw new Error(`HTTP ${result.status}: ${result.statusText}`);
                }
                
                // Extract filename from Content-Disposition header
                const filename = this.#extractFilename(result.headers, defaultFilename);
                
                return result.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                this.#triggerDownload(blob, filename);
                if (onSuccess) onSuccess(filename);
            })
            .catch(error => {
                if (onError) {
                    onError(error);
                } else {
                    console.error('Download failed:', error);
                }
            });
    }

    /**
     * Internal method to handle content-based downloads
     * @private
     */
    #downloadFromContent(content, filename, mimeType, onSuccess, onError) {
        try {
            // Auto-detect MIME type if not provided
            if (!mimeType) {
                mimeType = this.#detectMimeType(filename, content);
            }
            
            const blob = new Blob([content], { type: mimeType });
            this.#triggerDownload(blob, filename);
            
            if (onSuccess) onSuccess(filename);
        } catch (error) {
            if (onError) {
                onError(error);
            } else {
                console.error('Content download failed:', error);
            }
        }
    }

    /**
     * Extract filename from Content-Disposition header with robust parsing
     * @private
     */
    #extractFilename(headers, defaultFilename) {
        try {
            const contentDisposition = headers.get('Content-Disposition') || headers.get('content-disposition');
            
            if (!contentDisposition) {
                return defaultFilename;
            }
            
            // Handle both quoted and unquoted filenames
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                return filenameMatch[1].replace(/['"]/g, '').trim();
            }
            
            // Fallback to simple parsing
            const parts = contentDisposition.split(';');
            for (const part of parts) {
                if (part.trim().startsWith('filename=')) {
                    return part.split('=')[1].replace(/['"]/g, '').trim();
                }
            }
            
            return defaultFilename;
        } catch (error) {
            console.warn('Failed to parse Content-Disposition header:', error);
            return defaultFilename;
        }
    }

    /**
     * Auto-detect MIME type based on file extension and content
     * @private
     */
    #detectMimeType(filename, content) {
        const extension = filename.split('.').pop()?.toLowerCase();
        
        const mimeTypes = {
            'yaml': 'application/yaml',
            'yml': 'application/yaml',
            'json': 'application/json',
            'xml': 'application/xml',
            'csv': 'text/csv',
            'txt': 'text/plain',
            'html': 'text/html',
            'css': 'text/css',
            'js': 'application/javascript',
            'pdf': 'application/pdf',
            'zip': 'application/zip'
        };
        
        return mimeTypes[extension] || 'application/octet-stream';
    }

    /**
     * Trigger the actual download with proper cleanup
     * @private
     */
    #triggerDownload(blob, filename) {
        if (!blob) {
            throw new Error('No blob content to download');
        }
        
        const fileUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        
        link.href = fileUrl;
        link.download = filename;
        link.style.display = 'none';
        
        // Add to DOM, click, and cleanup
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up the blob URL to prevent memory leaks
        setTimeout(() => {
            window.URL.revokeObjectURL(fileUrl);
        }, 100);
    }
}

export {API_REST, HTTP_GET, HTTP_POST_FORM, HTTP_POST_JSON, HTTP_DELETE, HTTP_PUT};