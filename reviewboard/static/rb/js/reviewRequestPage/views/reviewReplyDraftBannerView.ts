import { BaseView, EventsHash, spina } from '@beanbag/spina';

import { ReviewReply } from 'reviewboard/common';
import { ReviewRequestEditor } from 'reviewboard/reviews';
import { FloatingBannerView } from 'reviewboard/ui';
import {
    FloatingBannerViewOptions,
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
    reviewRequestEditor: ReviewRequestEditor;
}


/**
 * A banner that represents a pending reply to a review.
 *
 * The banner offers actions for publishing and discarding the review.
 */
@spina
export class ReviewReplyDraftBannerView extends FloatingBannerView<
    ReviewReply,
    HTMLDivElement,
    ReviewReplyDraftBannerOptions
> {
    static className = 'banner';
    static events: EventsHash = {
        'click .discard-button': '_onDiscardClicked',
        'click .publish-button': '_onPublishClicked',
    };
    static modelEvents: EventsHash = {
        'publishError': '_onPublishError',
        'saved': '_onSaved',
        'saving destroying': '_onSavingOrDestroying',
    };

    private static template = _.template(dedent`
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
        </label>
        <% } %>
    `);

    /**********************
     * Instance variables *
     **********************/

    #reviewRequestEditor: ReviewRequestEditor;

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

        this.$el.html(ReviewReplyDraftBannerView.template({
            showSendEmail: this.#reviewRequestEditor.get('showSendEmail'),
        }));
    }

    /**
     * Handler for when Publish is clicked.
     *
     * Publishes the reply.
     */
    private _onPublishClicked() {
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
    private _onDiscardClicked() {
        this.model.destroy();
    }

    /**
     * Handler for when there's an error publishing.
     *
     * The error will be displayed in an alert.
     *
     * Args:
     *     errorText (string):
     *         The publish error text to show.
     */
    private _onPublishError(errorText: string) {
        alert(errorText);
    }

    /**
     * Handler for when the draft is saving or being destroyed.
     *
     * This will disable the buttons on the banner while the operation is
     * in progress.
     */
    private _onSavingOrDestroying() {
        this.$('input').prop('disabled', true);
    }

    /**
     * Handler for when the draft is saved.
     *
     * This will re-enable the buttons on the banner.
     */
    private _onSaved() {
        this.$('input').prop('disabled', false);
    }
}


/**
 * A static banner for review replies.
 *
 * This is used when the unified banner is enabled.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ReviewReplyDraftStaticBannerView extends BaseView {
    static className = 'banner';

    static template = _.template(dedent`
        <h1><%- draftText %></h1>
        <p><%- reminderText %></p>
    `);

    /**
     * Render the banner.
     */
    onInitialRender() {
        this.$el.html(ReviewReplyDraftStaticBannerView.template({
            draftText: _`This reply is a draft.`,
            reminderText: _`Be sure to publish when finished.`,
        }));
    }
}
