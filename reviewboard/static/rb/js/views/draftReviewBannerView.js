/*
 * A banner that represents a pending draft review.
 *
 * The banner displays at the top of the page and provides buttons for
 * editing the review, publishing, and discarding.
 *
 * The banner is a singleton. There's only ever one at a time.
 */
RB.DraftReviewBannerView = Backbone.View.extend({
    events: {
        'click #review-banner-edit': '_onEditReviewClicked',
        'click #review-banner-publish': '_onPublishClicked',
        'click #review-banner-discard': '_onDiscardClicked'
    },

    /*
     * Returns the height of the banner.
     */
    getHeight: function() {
        return this._$banner.outerHeight();
    },

    render: function() {
        var model = this.model;

        this._$buttons = this.$('input');
        this._$banner = this.$('.banner');

        model.on('saving destroying', function() {
            this._$buttons.prop('disabled', true);
        }, this);

        model.on('saved destroyed', function() {
            this._$buttons.prop('disabled', false);
        }, this);

        model.on('publishError', function(errorText) {
            alert(errorText);
        });

        return this;
    },

    /*
     * Shows the banner.
     *
     * The banner will appear to slide down from the top of the page.
     */
    show: function() {
        if (this.$el.is(':hidden')) {
            this.$el.slideDown();
            this._$banner
                .hide()
                .slideDown();
        }
    },

    /*
     * Hides the banner.
     *
     * The banner will slide up to the top of the page.
     *
     * A callback can be provided for after the banner is hidden.
     */
    hide: function(onDone, context) {
        this.$el.slideUp();
        this._$banner.slideUp();

        if (_.isFunction(onDone)) {
            this.$el.queue(_.bind(onDone, context));
        }
    },

    /*
     * Hides the banner and reloads the page.
     *
     * XXX Remove this function when we make the pages more dynamic.
     */
    hideAndReload: function() {
        this.hide(function() {
            /*
             * hideAndReload might have been called from within a $.funcQueue.
             * With Firefox, later async functions that are queued in the
             * $.funcQueue will not run when we change window.location, which
             * means that we might miss out on some teardown that was
             * scheduled. We defer changing the location until the next tick
             * of the event loop to let any teardown occur.
             */
            _.defer(_.bind(function() {
                window.location = this.model.get('parentObject').get('reviewURL');
            }, this));
        }, this);
    },

    /*
     * Handler for the Edit Review button.
     *
     * Displays the review editor dialog.
     */
    _onEditReviewClicked: function() {
        RB.ReviewDialogView.create({
            review: this.model,
            reviewRequestEditor: this.options.reviewRequestEditor
        });

        return false;
    },

    /*
     * Handler for the Publish button.
     *
     * Publishes the review.
     */
    _onPublishClicked: function() {
        this.model.publish({
            attrs: ['public']
        });
        return false;
    },

    /*
     * Handler for the Discard button.
     *
     * Prompts the user to confirm that they want the review discarded.
     * If they confirm, the review will be discarded.
     */
    _onDiscardClicked: function() {
        var model = this.model;

        $('<p/>')
            .text(gettext('If you discard this review, all related comments will be permanently deleted.'))
            .modalBox({
                title: gettext('Are you sure you want to discard this review?'),
                buttons: [
                    $('<input type="button" value="' + gettext('Cancel') + '"/>'),
                    $('<input type="button" value="' + gettext('Discard') + '"/>')
                        .click(function() {
                            model.destroy();
                        })
                ]
            });

        return false;
    }
}, {
    instance: null,

    /*
     * Creates the draft review banner singleton.
     */
    create: function(options) {
        if (!this.instance) {
            this.instance = new RB.DraftReviewBannerView(options);
            this.instance.render();
        }

        return this.instance;
    }
});
