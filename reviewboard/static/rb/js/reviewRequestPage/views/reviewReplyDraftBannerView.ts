import { spina } from '@beanbag/spina';
import {
    FloatingBannerView,
    FloatingBannerViewOptions
} from 'reviewboard/ui/views/floatingBannerView';


/**
 * Options for the ReviewReplyDraftBannerView.
 *
 * Version Added:
 *     6.0
 */
interface ReviewReplyDraftBannerOptions extends FloatingBannerViewOptions {
    /**
     * The review request editor.
     */
    reviewRequestEditor: RB.ReviewRequestEditor;
}


/**
 * A banner that represents a pending reply to a review.
 *
 * The banner offers actions for publishing and discarding the review.
 */
@spina
export class ReviewReplyDraftBannerView extends FloatingBannerView<
    RB.ReviewReply,
    HTMLDivElement,
    ReviewReplyDraftBannerOptions
> {
    className = 'banner';
    events = {
        'click .discard-button': this.#onDiscardClicked,
        'click .publish-button': this.#onPublishClicked,
    };
    modelEvents = {
        'publishError': errorText => alert(errorText),
        'saved': () => this.$('input').prop('disabled', false),
        'saving destroying': () => this.$('input').prop('disabled', true),
    };

    /**********************
     * Instance variables *
     **********************/
    #reviewRequestEditor: RB.ReviewRequestEditor;
    #template = _.template(dedent`
        <h1>${gettext('This reply is a draft.')}</h1>
        <p>${gettext('Be sure to publish when finished.')}</p>
        <span class="banner-actions">
         <input type="button" value="${gettext('Publish')}"
                class="publish-button" />
         <input type="button" value="${gettext('Discard')}"
                class="discard-button" />
        </span>
        <% if (showSendEmail) { %>
         <label>
          <input type="checkbox" class="send-email" checked />
          ${gettext('Send E-Mail')}
          <%- sendEmailText %>
        </label>
        <% } %>
    `);

    /**
     * Initialize the view.
     *
     * Args:
     *     options (ReviewReplyDraftBannerViewOptions):
     *         Options for the view.
     */
    initialize(options: ReviewReplyDraftBannerOptions) {
        super.initialize(options);
        this.#reviewRequestEditor = options.reviewRequestEditor;
    }

    /**
     * Render the banner.
     *
     * Returns:
     *     RB.ReviewRequestPage.ReviewReplyDraftBannerView:
     *     This object, for chaining.
     */
    onInitialRender() {
        super.onInitialRender();

        this.$el.html(this.#template({
            showSendEmail: this.#reviewRequestEditor.get('showSendEmail'),
        }));
    }

    /**
     * Handler for when Publish is clicked.
     *
     * Publishes the reply.
     */
    #onPublishClicked() {
        const $sendEmail = this.$('.send-email');

        this.model.publish({
            trivial: $sendEmail.length === 1 && !$sendEmail.is(':checked'),
        });
    }

    /**
     * Handler for when Discard is clicked.
     *
     * Discards the reply.
     */
    #onDiscardClicked() {
        this.model.destroy();
    }
}
