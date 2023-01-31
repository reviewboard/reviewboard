/**
 * A banner that represents a pending draft review.
 *
 * The banner displays at the top of the page and provides buttons for
 * editing the review, publishing, and discarding.
 *
 * The banner is a singleton. There's only ever one at a time.
 */
RB.DraftReviewBannerView = Backbone.View.extend({
    events: {
        'click #review-banner-discard': '_onDiscardClicked',
        'click #review-banner-edit': '_onEditReviewClicked',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     reviewRequestEditor (RB.ReviewRequestEditor):
     *         The review request editor.
     */
    initialize(options) {
        this.options = options;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.DraftReviewBannerView:
     *     This object, for chaining.
     */
    render() {
        this._$buttons = this.$('input');
        this._$banner = this.$('.banner');

        const model = this.model;
        this.listenTo(model, 'saving destroying',
                      () => this._$buttons.prop('disabled', true));
        this.listenTo(model, 'saved destroyed',
                      () => this._$buttons.prop('disabled', false));
        this.listenTo(model, 'publishError', errorText => alert(errorText));

        this._publishButton = new RB.MenuButtonView({
            ariaMenuLabel: gettext('More publishing options'),
            el: this.$('#review-banner-publish-container'),
            id: 'review-banner-publish',
            menuItems: [
                {
                    id: 'review-banner-publish-submitter-only',
                    onClick: () => this._onPublishClicked({
                        publishToOwnerOnly: true,
                    }),
                    text: _`... and only e-mail the owner`,
                },
                {
                    id: 'review-banner-publish-and-archive',
                    onClick: () => this._onPublishClicked({
                        publishAndArchive: true,
                    }),
                    text: _`... and archive the review request`,
                },
            ],
            onPrimaryButtonClick: () => this._onPublishClicked(),
            text: gettext('Publish Review'),
        });

        this._publishButton.render();

        if (!this.$el.prop('hidden')) {
            this.show();
        }

        this.$el.addClass('ui-ready');

        return this;
    },

    /*
     * Show the banner.
     *
     * The banner will appear to slide down from the top of the page.
     */
    show() {
        const height = this._$banner.outerHeight();

        RB.scrollManager.markForUpdate(this.$el);

        this.$el
            .prop('hidden', false)
            .removeClass('hidden')
            .css({
                height: height,
                maxHeight: height,
            });
        RB.scrollManager.scrollYOffset += height;
        RB.scrollManager.markUpdated(this.$el);
    },

    /*
     * Hide the banner.
     *
     * The banner will slide up to the top of the page.
     */
    hide() {
        RB.scrollManager.markForUpdate(this.$el);

        const height = this._$banner.outerHeight();

        this.$el
            .prop('hidden', true)
            .addClass('hidden')
            .css('max-height', '');

        /*
         * If we set the height immediately, the browser will appear to not
         * animate, since it can't transition heights (only max-heights). So
         * we delay for a short period after we know the transition will have
         * completed.
         */
        _.delay(
            () => {
                this.$el.css('height', '');
                RB.scrollManager.markUpdated(this.$el);
                RB.scrollManager.scrollYOffset -= height;
            },
            500);
    },

    /**
     * Hide the banner and reloads the page.
     *
     * XXX Remove this function when we make the pages more dynamic.
     */
    hideAndReload() {
        this.hide();

        /*
         * hideAndReload might have been called from within a $.funcQueue.
         * With Firefox, later async functions that are queued in the
         * $.funcQueue will not run when we change window.location, which
         * means that we might miss out on some teardown that was
         * scheduled. We defer changing the location until the next tick
         * of the event loop to let any teardown occur.
         */
        _.defer(() => {
            RB.navigateTo(this.model.get('parentObject').get('reviewURL'));
        });
    },

    /**
     * Return the height of the banner.
     *
     * Returns:
     *     number:
     *     The height of the banner.
     */
    getHeight() {
        return this._$banner.outerHeight();
    },

    /**
     * Remove the banner from the page.
     */
    remove() {
        if (this._publishButton) {
            this._publishButton.remove();
        }

        _super(this).remove.call(this);
    },

    /**
     * Handler for the Edit Review button.
     *
     * Displays the review editor dialog.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _onEditReviewClicked() {
        RB.ReviewDialogView.create({
            review: this.model,
            reviewRequestEditor: this.options.reviewRequestEditor,
        });

        return false;
    },

    /**
     * Handler for the Publish button.
     *
     * Publishes the review.
     *
     * Args:
     *     options (object):
     *         Options that determine special cases for submission.
     *
     * Option Args:
     *     publishToOwnerOnly (boolean):
     *         Whether or not we should only notify the submitter of the
     *         review.
     *
     *     publishAndArchive (boolean):
     *         Whether or not we should archive the review after it is
     *         published.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _onPublishClicked(options={}) {
        if (options.publishToOwnerOnly) {
            this.model.set('publishToOwnerOnly', true);
        }

        if (options.publishAndArchive) {
            this.model.set('publishAndArchive', true);
        }

        this.model.publish({
            attrs: ['public', 'publishToOwnerOnly', 'publishAndArchive'],
        });

        return false;
    },

    /**
     * Handler for the Discard button.
     *
     * Prompts the user to confirm that they want the review discarded.
     * If they confirm, the review will be discarded.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _onDiscardClicked() {
        $('<p/>')
            .text(_`If you discard this review, all related comments will be permanently deleted.`)
            .modalBox({
                buttons: [
                    $('<input type="button">')
                        .val(_`Cancel`),
                    $('<input type="button">')
                        .val(_`Discard`)
                        .click(() => this.model.destroy()),
                ],
                title: _`'Are you sure you want to discard this review?`,
            });

        return false;
    },
}, {
    instance: null,

    /**
     * Create the draft review banner singleton.
     *
     * Returns:
     *     RB.DraftReviewBannerView:
     *     The banner view.
     */
    create(options) {
        if (!this.instance) {
            this.instance = new RB.DraftReviewBannerView(options);
            this.instance.render();
        }

        return this.instance;
    },
});
