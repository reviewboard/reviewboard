/**
 * Action for logging out via POST request.
 *
 * Version Added:
 *     8.0
 */

import {
    spina,
} from '@beanbag/spina';

import { Action } from './actionModel';


/**
 * Action for logging out.
 *
 * This overrides the default activate behavior to submit a POST request
 * with a CSRF token, as required by Django's LogoutView.
 *
 * Version Added:
 *     8.0
 */
@spina
export class LogoutAction extends Action {
    /**********************
     * Instance variables *
     **********************/

    /** The URL to POST to for logout. */
    #logoutUrl: string;

    /**
     * Initialize the action.
     *
     * This saves the logout URL and sets the action's URL to '#' to
     * prevent direct navigation, allowing activate() to handle the
     * logout via POST.
     */
    initialize() {
        super.initialize();

        this.#logoutUrl = this.get('url');
        this.set('url', '#');
    }

    /**
     * Activate the action.
     *
     * This submits a POST form to the logout URL with the CSRF token,
     * as Django's LogoutView no longer accepts GET requests.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate(): Promise<void> {
        const url = this.#logoutUrl;
        const csrfToken = this.#getCSRFToken();

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        form.style.display = 'none';

        if (csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
        }

        document.body.appendChild(form);
        form.submit();
    }

    /**
     * Extract the CSRF token from cookies.
     *
     * Returns:
     *     string:
     *     The CSRF token, or null if not found.
     */
    #getCSRFToken(): string | null {
        const cookies = document.cookie.split(';');

        for (const cookie of cookies) {
            const trimmed = cookie.trim();

            if (trimmed.startsWith('csrftoken=')) {
                return trimmed.substring('csrftoken='.length);
            }
        }

        return null;
    }
}
