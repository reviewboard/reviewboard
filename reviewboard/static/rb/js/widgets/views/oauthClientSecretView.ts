/**
 * A view for editing an OAuth client secret.
 */
import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';


/**
 * Options for the OAuthClientSecretView.
 *
 * Version Added:
 *     8.0
 */
interface OAuthClientSecretViewOptions {
    /** The URL of the API endpoint for the OAuth application. */
    apiURL: string;
}


/**
 * A view for editing an OAuth client secret.
 *
 * This view hits the API to regenerate the associated application's
 * client secret and updates the ``<input>`` element with the updated value. It
 * also bundles a copy button so that the value can be copied to the user's
 * clipboard.
 */
@spina
export class OAuthClientSecretView extends BaseView<
    undefined,
    HTMLDivElement,
    OAuthClientSecretViewOptions
> {
    static events: EventsHash ={
        'click .copyable-text-input-link': '_onCopyClicked',
        'click .regenerate-secret-button': '_onRegenerateClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The text input element. */
    #$input: JQuery;

    /** The "regenerate client secret" button. */
    #$regen: JQuery;

    /** The URL of the API endpoint for the OAuth application. */
    #apiURL: string;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (OAuthClientSecretViewOptions):
     *         The view options.
     */
    initialize(options: OAuthClientSecretViewOptions) {
        this.#apiURL = options.apiURL;
    }

    /**
     * Render the view.
     */
    protected onRender() {
        this.#$input = this.$('input');
        this.#$regen = this.$('.regenerate-secret-button');
    }

    /**
     * Copy the client secret to the clipboard.
     *
     * Args:
     *     e (Event):
     *         The click event that triggered this handler.
     */
    private async _onCopyClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        /*
         * We don't actually need to select the input text when using
         * navigator.clipboard, but that makes it clearer that something
         * happened, and makes it visually match the behavior of
         * djblets.forms.widgets.CopyableTextWidget, which is used for the
         * Client ID.
         */
        this.#$input
            .trigger('focus')
            .trigger('select');

        const token = this.#$input.val() as string;
        await navigator.clipboard.writeText(token);
    }

    /**
     * Regenerate the client secret.
     *
     * Args:
     *     e (Event):
     *         The click event that triggered this handler.
     */
    private async _onRegenerateClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this.#$regen.attr('aria-busy', 'true');

        RB.apiCall({
            data: {
                'regenerate_client_secret': 1,
            },
            error: () => {
                this.#$regen.attr('aria-busy', 'false');
            },
            method: 'PUT',
            success: rsp => {
                this.#$input.val(rsp.oauth_app.client_secret);
                this.#$regen.attr('aria-busy', 'false');
            },
            url: this.#apiURL,
        });
    }
}
