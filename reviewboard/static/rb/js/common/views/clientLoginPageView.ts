/**
 * A view for the client login page.
 */

import { spina } from '@beanbag/spina';

import {
    type Page,
} from '../models/pageModel';
import {
    type PageViewOptions,
    PageView,
} from './pageView';


/**
 * Options for the ClientLoginPageView.
 *
 * Version Added:
 *     8.0
 */
export interface ClientLoginPageViewOptions extends PageViewOptions {
    /** The name of the client. */
    clientName: string;

    /** The URL of where to send the authentication data. */
    clientURL: string;

    /**
     * Authentication data to send to the client.
     *
     * This must be JSON-serializable.
     */
    payload: Record<string, unknown>;

    /**
     * An optional URL of where to redirect to.
     *
     * This will be used after successfully sending the authentication data
     * to the client.
     */
    redirectTo: string;

    /** The username of the user who is authenticating the client. */
    username: string;

    /**
     * Whether to wait to send data to the client.
     *
     * This is used during unit tests to allow us to explicitly call sendData.
     */
    waitToSend?: boolean;
}


/**
 * A view for the client login page.
 *
 * This view sends authentication data to a client to authenticate
 * it to Review Board for a user.
 *
 * Version Changed:
 *     8.0:
 *     Renamed from ClientLoginView to ClientLoginPageView and updated to
 *     inherit from PageView.
 *
 * Version Added:
 *     5.0.5
 */
@spina
export class ClientLoginPageView extends PageView<
    Page,
    HTMLBodyElement,
    ClientLoginPageViewOptions
> {
    static contentTemplate = _.template(dedent`
        <h1><%- header %></h1>
        <p><%- message %><span id="redirect-counter"><%- count %></span></p>`
    );

    /**********************
     * Instance variables *
     **********************/

    /** The saved options. */
    options: ClientLoginPageViewOptions = null;

    /**
     * The number of seconds left before the page redirects.
     *
     * After a successful login, we show a countdown before the page redirects.
     *
     * This is public for consumption in unit tests.
     */
    _redirectInSeconds = 3;

    /**
     * The URL to redirect to after a successful authentication.
     *
     * This is public for consumption in unit tests.
     */
    _redirectTo: string;

    /**
     * The timeout interval for the redirect countdown.
     */
    #redirectCounterInterval: number;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (ClientLoginPageViewOptions):
     *         The view options.
     */
    initialize(options: ClientLoginPageViewOptions) {
        super.initialize(options);

        this._redirectTo = decodeURIComponent(options.redirectTo);
    }

    /**
     * Render the view.
     */
    renderPage() {
        if (!this.options.waitToSend) {
            this.sendData();
        }
    }

    /**
     * Send the data to the server.
     */
    async sendData() {
        const $content = this.$pageContent.children('#auth_container');
        const options = this.options;
        const clientName = options.clientName;
        const clientURL = decodeURIComponent(options.clientURL);
        const username = options.username;
        const redirectCounter = this._redirectInSeconds;

        let rsp: Response;

        try {
            rsp = await fetch(clientURL, {
                body: JSON.stringify(options.payload),
                headers: {
                    'Content-Type': 'application/json; charset=UTF-8',
                },
                method: 'POST',
                mode: 'cors',
            });
        } catch (error) {
            $content.html(ClientLoginPageView.contentTemplate({
                count: '',
                header: _`Failed to log in for ${clientName}`,
                message: _`Could not connect to ${clientName}.
                           Please contact your administrator.`,
            }));

            return;
        }

        if (rsp.ok) {
            if (this._redirectTo) {
                $content.html(ClientLoginPageView.contentTemplate({
                    count: ` ${redirectCounter}...`,
                    header: _`Logged in to ${clientName}`,
                    message: _`You have successfully logged in to
                               ${clientName} as ${username}. Redirecting in`,
                }));

                this.#redirectCounterInterval = window.setInterval(
                    this._redirectCountdown.bind(this),
                    1000);
            } else {
                $content.html(ClientLoginPageView.contentTemplate({
                    count: '',
                    header: _`Logged in to ${clientName}`,
                    message: _`You have successfully logged in to
                               ${clientName} as ${username}. You can now
                               close this page.`,
                }));
            }
        } else {
            $content.html(ClientLoginPageView.contentTemplate({
                count: '',
                header: _`Failed to log in for ${clientName}`,
                message: _`Failed to log in for ${clientName} as ${username}.
                           Please contact your administrator.`,
            }));
        }
    }

    /**
     * Display a countdown and then redirect to a URL.
     *
     * This is public for consumption in unit tests.
     */
    _redirectCountdown() {
        const redirectCounter = --this._redirectInSeconds;

        this.$('#redirect-counter').text(` ${redirectCounter}...`);

        if (redirectCounter <= 0) {
            clearInterval(this.#redirectCounterInterval);
            RB.navigateTo(this._redirectTo);
        }
    }
}
