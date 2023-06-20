/**
 * A view for the client login page.
 *
 * This view sends authentication data to a client to authenticate
 * it to Review Board for a user.
 *
 * Version Added:
 *     5.0.5
 */
RB.ClientLoginView = Backbone.View.extend({
    contentTemplate: _.template(dedent`
        <h1><%- header %></h1>
        <p><%- message %><span id="redirect-counter"><%- count %></span></p>`
    ),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         The view options.
     *
     * Option Args:
     *     clientName (string):
     *         The name of the client.
     *
     *     clientURL (string):
     *         The URL of where to send the authentication data.
     *
     *     payload (string):
     *         A JSON string containing the authentication data to send to
     *         the client.
     *
     *     redirectTo (string):
     *         An optional URL of where to redirect to after successfully
     *         sending the authentication data to the client.
     *
     *     username (string):
     *         The username of the user who is authenticating the client.
     */
    initialize(options) {
        this._clientName = options.clientName;
        this._clientURL = decodeURIComponent(options.clientURL);
        this._payload = options.payload;
        this._redirectTo = decodeURIComponent(options.redirectTo);
        this._username = options.username;
        this._redirectCounter = 3;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.ClientLoginView:
     *     This view.
     */
    async render() {
        let rsp;
        const clientName = this._clientName;
        const username = this._username;
        const redirectCounter = this._redirectCounter;
        const $content = this.$('.auth-header');

        try {
            rsp = await this._sendDataToClient();
        } catch (error) {
            $content.html(this.contentTemplate({
                count: '',
                header: _`Failed to log in for ${clientName}`,
                message: _`Could not connect to ${clientName}.
                           Please contact your administrator.`,
            }));

            return this;
        }

        if (rsp.ok) {
            if (this._redirectTo) {
                $content.html(this.contentTemplate({
                    count: ` ${redirectCounter}...`,
                    header: _`Logged in to ${clientName}`,
                    message: _`You have successfully logged in to
                               ${clientName} as ${username}. Redirecting in`,
                }));

                this._$counter = $('#redirect-counter');
                this._interval = setInterval(
                    this._redirectCountdown.bind(this),
                    1000);
            } else {
                $content.html(this.contentTemplate({
                    count: '',
                    header: _`Logged in to ${clientName}`,
                    message: _`You have successfully logged in to
                               ${clientName} as ${username}. You can now
                               close this page.`,
                }));
            }
        } else {
            $content.html(this.contentTemplate({
                count: '',
                header: _`Failed to log in for ${clientName}`,
                message: _`Failed to log in for ${clientName} as ${username}.
                           Please contact your administrator.`,
            }));
        }

        return this;
    },

    /**
     * Display a countdown and then redirect to a URL.
     */
    _redirectCountdown() {
        const redirectCounter = --this._redirectCounter;
        this._$counter.text(` ${redirectCounter}...`);

        if (redirectCounter <= 0) {
            clearInterval(this._interval);
            RB.navigateTo(this._redirectTo);
        }
    },

    /**
     * Send authentication data to the client.
     *
     * Returns:
     *     A promise which resolves to a Response object when the request
     *     is complete.
     */
    async _sendDataToClient() {
        let rsp = await fetch(this._clientURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=UTF-8',
            },
            body: JSON.stringify(this._payload),
        });

        return rsp;
    },
});