/**
 * The unified banner view.
 */
import { BaseView, spina } from '@beanbag/spina';

import { FloatingBannerView } from 'reviewboard/ui/views/floatingBannerView';
import { MenuButtonView } from 'reviewboard/ui/views/menuButtonView';
import { MenuType, MenuView } from 'reviewboard/ui/views/menuView';

import { UnifiedBanner } from '../models/unifiedBanner';


/**
 * A view for a dropdown menu within the unified banner.
 *
 * Version Added:
 *     6.0
 */
@spina
class DraftModeMenu extends BaseView<UnifiedBanner> {
    className = 'rb-c-unified-banner__menu';

    /**********************
     * Instance variables *
     **********************/

    #$arrow: JQuery;
    #$label: JQuery;
    #menuView: MenuView;

    /**
     * The events to listen to.
     */
    events = {
        'focusout': this.#onFocusOut,
        'keydown': this.#onKeyDown,
        'mouseenter': this.#openMenu,
        'mouseleave': this.#closeMenu,
    };

    modelEvents = {
        'change:draftModes change:selectedDraftMode': this.#update,
    };

    /**
     * Render the view.
     */
    onInitialRender() {
        const label = _`Mode`;

        this.#menuView = new MenuView({
            $controller: this.$el,
            ariaLabel: label,
        });

        this.$el.html(dedent`
            <a class="rb-c-unified-banner__mode" tabindex="0">
             <span class="rb-c-unified-banner__menu-label">
              <span class="rb-icon rb-icon-edit-review"></span>
              ${label}
             </span>
             <span class="rb-icon rb-icon-dropdown-arrow"></span>
            </a>
        `);

        this.#menuView.renderInto(this.$el);

        this.#$label = this.$('.rb-c-unified-banner__menu-label');
        this.#$arrow = this.$('.rb-icon-dropdown-arrow');

        this.#update();
    }

    /**
     * Open the menu.
     */
    #openMenu() {
        if (this.#menuView.$el.children().length > 0) {
            this.#menuView.open({
                animate: false,
            });
        }
    }

    /**
     * Close the menu.
     */
    #closeMenu() {
        if (this.#menuView.$el.children().length > 0) {
            this.#menuView.close({
                animate: false,
            });
        }
    }

    /**
     * Handle a focus-out event.
     *
     * Args:
     *     evt (FocusEvent):
     *         The event object.
     */
    #onFocusOut(evt: FocusEvent) {
        evt.stopPropagation();

        /*
         * Only close the menu if the focus has moved to something outside of
         * this component.
         */
        const currentTarget = evt.currentTarget as Element;

        if (!currentTarget.contains(evt.relatedTarget as Element)) {
            this.#menuView.close({
                animate: false,
            });
        }
    }

    /**
     * Handle a key down event.
     *
     * When the menu has focus, this will take care of handling keyboard
     * operations, allowing the menu to be opened or closed. Opening the menu
     * will transfer the focus to the menu items.
     *
     * Args:
     *     evt (KeyboardEvent):
     *         The keydown event.
     */
    #onKeyDown(evt: KeyboardEvent) {
        if (evt.key === 'ArrowDown' ||
            evt.key === 'ArrowUp' ||
            evt.key === 'Enter' ||
            evt.key === ' ') {
            evt.preventDefault();
            evt.stopPropagation();

            this.#menuView.open({
                animate: false,
            });
            this.#menuView.focusFirstItem();
        } else if (evt.key === 'Escape') {
            evt.preventDefault();
            evt.stopPropagation();

            this.#menuView.close({
                animate: false,
            });
        }
    }

    /**
     * Update the state of the draft mode selector.
     */
    #update() {
        const model = this.model;
        const draftModes = model.get('draftModes');
        const selectedDraftMode = model.get('selectedDraftMode');

        this.#menuView.clearItems();

        for (let i = 0; i < draftModes.length; i++) {
            const text = draftModes[i].text;

            if (i === selectedDraftMode) {
                this.#$label.html(dedent`
                    <span class="rb-icon rb-icon-edit-review"></span>
                    ${text}
                    `);
            } else {
                this.#menuView.addItem({
                    onClick: () => model.set('selectedDraftMode', i),
                    text: text,
                });
            }
        }

        this.#$arrow.setVisible(draftModes.length > 1);
    }
}


/**
 * The publish button.
 *
 * Version Added:
 *     6.0
 */
@spina
class PublishButtonView extends MenuButtonView<UnifiedBanner> {
    modelEvents = {
        'change:draftModes change:selectedDraftMode': this.#update,
    };

    /**********************
     * Instance variables *
     **********************/

    #$archiveCheckbox: JQuery;
    #$trivialCheckbox: JQuery;

    /**
     * Initialize the view.
     */
    initialize() {
        super.initialize({
            ariaMenuLabel: _`Publish All`,
            hasPrimaryButton: true,
            menuIconClass: 'fa fa-gear',
            menuType: MenuType.Button,
            onPrimaryButtonClick: this.#onPublishClicked,
            text: _`Publish All`,
        });
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        super.onInitialRender();

        this.#$trivialCheckbox = $(
            '<input checked type="checkbox" id="publish-button-trivial">');
        this.#$archiveCheckbox = $(
            '<input type="checkbox" id="publish-button-archive">');

        const reviewRequestEditor = this.model.get('reviewRequestEditor');

        if (reviewRequestEditor.get('showSendEmail')) {
            const $onlyEmail = this.menu.addItem()
                .append(this.#$trivialCheckbox);

            $('<label for="publish-button-trivial">')
                .text(_`Send E-Mail`)
                .appendTo($onlyEmail);
        }

        const $archive = this.menu.addItem()
            .append(this.#$archiveCheckbox);

        $('<label for="publish-button-archive">')
            .text(_`Archive after publishing`)
            .appendTo($archive);

        this.#update();
    }

    /**
     * Callback for when the publish button is clicked.
     */
    #onPublishClicked() {
        this.trigger('publish', {
            archive: this.#$archiveCheckbox.is(':checked'),
            trivial: !this.#$trivialCheckbox.is(':checked'),
        });
    }

    /**
     * Update the state of the publish button.
     */
    #update() {
        const draftModes = this.model.get('draftModes');
        const selectedDraftMode = this.model.get('selectedDraftMode');

        if (!this.rendered || draftModes.length === 0) {
            return;
        }

        if (draftModes[selectedDraftMode].multiple) {
            this.$primaryButton.text(_`Publish All`);
        } else {
            this.$primaryButton.text(_`Publish`);
        }
    }
}


/**
 * Options for the unified banner view.
 *
 * Version Added:
 *     6.0
 */
interface UnifiedBannerViewOptions {
    /** The review request editor. */
    reviewRequestEditorView: RB.ReviewRequestEditorView;
}


/**
 * The unified banner.
 *
 * This is a unified, multi-mode banner that provides basic support for
 * publishing, editing, and discarding reviews, review requests, and
 * review replies.
 *
 * The banner displays at the top of the page under the topbar and floats to
 * the top of the browser window when the user scrolls down.
 *
 * Version Added:
 *     6.0
 */
@spina
export class UnifiedBannerView extends FloatingBannerView<
    UnifiedBanner,
    HTMLDivElement,
    UnifiedBannerViewOptions
> {
    static instance: UnifiedBannerView = null;

    events = {
        'click #btn-review-request-discard': this.#discardDraft,
    };

    modelEvents = {
        'change': this.#update,
        'change:selectedDraftMode': this.#scrollToReviewReply,
    };

    /**********************
     * Instance variables *
     **********************/

    #$changedesc: JQuery;
    #$discardButton: JQuery;
    #$draftActions: JQuery;
    #$modeSelector: JQuery;
    #$reviewActions: JQuery;
    #modeMenu: DraftModeMenu;
    #publishButton: PublishButtonView;
    #reviewRequestEditorView: RB.ReviewRequestEditorView;

    /**
     * Reset the UnifiedBannerView instance.
     *
     * This is used in unit tests to reset the state after tests run.
     */
    static resetInstance() {
        if (this.instance !== null) {
            this.instance.remove();
            this.instance = null;
        }
    }

    /**
     * Return the UnifiedBannerView instance.
     *
     * If the banner does not yet exist, this will create it.
     *
     * Args:
     *     required (boolean, optional):
     *         Whether the instance is required to exist.
     *
     * Returns:
     *     RB.UnifiedBannerView:
     *     The banner view.
     */
    static getInstance(
        required = false,
    ): UnifiedBannerView {
        if (required) {
            console.assert(
                this.instance,
                'Unified banner instance has not been created');
        }

        return this.instance;
    }

    /**
     * Initialize the banner.
     *
     * Args:
     *     options (object):
     *         Options for the banner. See :js:class:`RB.FloatingBannerView`
     *         for details.
     */
    initialize(options: UnifiedBannerViewOptions) {
        super.initialize(_.defaults(options, {
            $floatContainer: $('#page-container'),
            noFloatContainerClass: 'collapsed',
        }));

        this.#reviewRequestEditorView = options.reviewRequestEditorView;
        UnifiedBannerView.instance = this;
    }

    /**
     * Render the banner.
     */
    onInitialRender() {
        if (!RB.UserSession.instance.get('authenticated')) {
            return;
        }

        super.onInitialRender();

        const model = this.model;

        this.#$modeSelector = this.$('.rb-c-unified-banner__mode-selector');
        this.#$draftActions = this.$('.rb-c-unified-banner__draft-actions');
        this.#$reviewActions = this.$('.rb-c-unified-banner__review-actions');
        this.#$changedesc = this.$('.rb-c-unified-banner__changedesc');

        this.#modeMenu = new DraftModeMenu({
            model: model,
        });
        this.#modeMenu.renderInto(this.#$modeSelector);

        this.#publishButton = new PublishButtonView({
            model: model,
        });
        this.#publishButton.$el.prependTo(this.#$draftActions);
        this.listenTo(this.#publishButton, 'publish', this.publish);
        this.#publishButton.render();

        this.#$discardButton = this.$('#btn-review-request-discard');

        const reviewRequestEditor = model.get('reviewRequestEditor');
        const reviewRequest = model.get('reviewRequest');

        const $changeDescription = this.$('#field_change_description')
            .html(reviewRequestEditor.get('changeDescriptionRenderedText'))
            .toggleClass('editable', reviewRequestEditor.get('mutableByUser'))
            .toggleClass('rich-text',
                         reviewRequest.get('changeDescriptionRichText'));

        this.#reviewRequestEditorView.addFieldView(
            new RB.ReviewRequestFields.ChangeDescriptionFieldView({
                el: $changeDescription,
                fieldID: 'change_description',
                model: reviewRequestEditor,
            }));
    }

    /**
     * Handle re-renders.
     */
    onRender() {
        this.#update();
    }

    /**
     * Update the state of the banner.
     */
    #update() {
        if (!this.rendered) {
            return;
        }

        const model = this.model;
        const draftModes = model.get('draftModes');
        const selectedDraftMode = model.get('selectedDraftMode');
        const numDrafts = model.get('numDrafts');

        const reviewRequest = model.get('reviewRequest');
        const reviewRequestState = reviewRequest.get('state');
        const reviewRequestPublic = reviewRequest.get('public');

        this.#$discardButton.setVisible(
            draftModes.length > 0 &&
            !draftModes[selectedDraftMode].multiple);
        this.#$modeSelector.setVisible(numDrafts > 0);
        this.#$draftActions.setVisible(numDrafts > 0);
        this.#$changedesc.setVisible(
            reviewRequestPublic &&
            draftModes.length > 0 &&
            draftModes[selectedDraftMode].hasReviewRequest);

        this.$el
            .toggleClass('-has-draft',
                         (reviewRequestPublic === false || numDrafts > 0))
            .toggleClass('-has-multiple', numDrafts > 1)
            .setVisible(reviewRequestState === RB.ReviewRequest.PENDING);
    }

    /**
     * Return the height of the banner.
     *
     * Returns:
     *     number:
     *     The height of the banner, in pixels.
     */
    getHeight(): number {
        return this.$el.outerHeight();
    }

    /**
     * Publish the current draft.
     *
     * This triggers an event which is handled by RB.ReviewRequestEditorView.
     */
    async publish(
        options: {
            archive: boolean,
            trivial: boolean,
        },
    ): Promise<void> {
        const model = this.model;
        const selectedDraftMode = model.get('selectedDraftMode');
        const draftModes = model.get('draftModes');
        const draftMode = draftModes[selectedDraftMode];
        const reviewRequestEditor = model.get('reviewRequestEditor');
        const reviewRequest = reviewRequestEditor.get('reviewRequest');
        const pendingReview = model.get('pendingReview');
        const reviewReplyDrafts = model.get('reviewReplyDrafts');

        const reviews: number[] = [];
        const reviewRequests: number[] = [];

        if (draftMode.hasReviewRequest) {
            await reviewRequest.ready();
            reviewRequests.push(reviewRequest.get('id'));
        }

        if (draftMode.hasReview) {
            await pendingReview.ready();
            reviews.push(pendingReview.get('id'));
        }

        if (draftMode.singleReviewReply !== undefined) {
            const reply = reviewReplyDrafts[draftMode.singleReviewReply];
            await reply.ready();
            reviews.push(reply.get('id'));
        } else if (draftMode.hasReviewReplies) {
            for (const reply of reviewReplyDrafts) {
                await reply.ready();
                reviews.push(reply.get('id'));
            }
        }

        try {
            await this.#runPublishBatch(reviewRequest.get('localSitePrefix'),
                                        reviewRequests,
                                        reviews,
                                        !!options.trivial,
                                        !!options.archive);
        } catch (err) {
            alert(err);
        }

        RB.navigateTo(reviewRequest.get('reviewURL'));
    }

    /**
     * Run the publish batch operation.
     *
     * Args:
     *     localSitePrefix (string):
     *         The URL prefix for the local site, if present.
     *
     *     reviewRequests (Array of number):
     *         The set of review request IDs to publish.
     *
     *     reviews (Array of number):
     *         The set of review IDs to publish.
     *
     *     trivial (boolean):
     *         Whether to suppress notification e-mails.
     *
     *     archive (boolean):
     *         Whether to archive the affected review request after publishing.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete or rejects
     *     with an error string.
     */
    #runPublishBatch(
        localSitePrefix: string,
        reviewRequests: number[],
        reviews: number[],
        trivial: boolean,
        archive: boolean,
    ): Promise<void> {
        return new Promise((resolve, reject) => {
            RB.apiCall({
                data: {
                    batch: JSON.stringify({
                        archive: archive,
                        op: 'publish',
                        review_requests: reviewRequests,
                        reviews: reviews,
                        trivial: trivial,
                    }),
                },
                prefix: localSitePrefix,
                url: '/r/_batch/',

                error: xhr => {
                    const rsp = xhr.responseJSON;

                    if (rsp && rsp.stat) {
                        reject(rsp.error);
                    } else {
                        console.error(
                            'Failed to run publish batch operation', xhr);
                        reject(xhr.statusText);
                    }
                },
                success: () => {
                    resolve();
                },
            });
        });
    }

    /**
     * Discard the current draft.
     *
     * Depending on the selected view mode, this will either discard the
     * pending review, discard the current review request draft, or close the
     * (unpublished) review request as discarded.
     */
    async #discardDraft() {
        const model = this.model;
        const selectedDraftMode = model.get('selectedDraftMode');
        const draftModes = model.get('draftModes');
        const draftMode = draftModes[selectedDraftMode];
        const reviewRequest = model.get('reviewRequest');

        try {
            if (draftMode.hasReview) {
                const pendingReview = model.get('pendingReview');
                await pendingReview.destroy();

                RB.navigateTo(reviewRequest.get('reviewURL'));
            } else if (draftMode.hasReviewRequest) {
                if (!reviewRequest.get('public')) {
                    await reviewRequest.close({
                        type: RB.ReviewRequest.CLOSE_DISCARDED,
                    });
                } else if (!reviewRequest.draft.isNew()) {
                    await reviewRequest.draft.destroy();
                }

                RB.navigateTo(reviewRequest.get('reviewURL'));
            } else if (draftMode.singleReviewReply !== undefined) {
                const reviewReplyDrafts = model.get('reviewReplyDrafts');
                const reply = reviewReplyDrafts[draftMode.singleReviewReply];

                await reply.destroy();
            } else {
                console.error('Discard reached with no active drafts.');
            }
        } catch(err) {
            alert(err.xhr.errorText);
        }
    }

    /**
     * Handler for when the selected draft mode changes.
     *
     * If the newly selected mode is a review reply, scroll the document to
     * that review.
     */
    #scrollToReviewReply() {
        const selectedDraftMode = this.model.get('selectedDraftMode');
        const draftModes = this.model.get('draftModes');
        const draftMode = draftModes[selectedDraftMode];

        if (draftMode.singleReviewReply !== undefined) {
            const reviewReplyDrafts = this.model.get('reviewReplyDrafts');
            const reply = reviewReplyDrafts[draftMode.singleReviewReply];
            const originalReview = reply.get('parentObject').get('id');

            const $review = $(`#review${originalReview}`);
            const reviewTop = $review.offset().top;
            const bannerHeight = this.$el.outerHeight(true);

            $(document).scrollTop(reviewTop - bannerHeight - 20);
        }
    }
}
