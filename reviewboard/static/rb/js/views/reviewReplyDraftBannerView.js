/*
 * A banner that represents a pending reply to a review.
 *
 * The banner offers actions for publishing and discarding the review.
 */
RB.ReviewReplyDraftBannerView = RB.FloatingBannerView.extend({
    className: 'banner',

    template: _.template([
        '<h1><%- draftText %></h1>',
        '<p>Be sure to publish when finished.</p>',
        '<span class="banner-actions">',
        ' <input type="button" value="<%- publishText %>"',
        '        class="publish-button" />',
        ' <input type="button" value="<%- discardText %>"',
        '        class="discard-button" />',
        '</span>'
    ].join('')),

    events: {
        'click .publish-button': '_onPublishClicked',
        'click .discard-button': '_onDiscardClicked'
    },

    /*
     * Renders the banner.
     */
    render: function() {
        _super(this).render.call(this);

        this.$el.html(this.template({
            draftText: gettext('This reply is a draft.'),
            publishText: gettext('Publish'),
            discardText: gettext('Discard')
        }));

        this.model.on('saving destroying', function() {
            this.$('input').prop('disabled', true);
        }, this);

        this.model.on('saved', function() {
            this.$('input').prop('disabled', false);
        }, this);

        this.model.on('publishError', function(errorText) {
            alert(errorText);
        }, this);

        return this;
    },

    /*
     * Handler for when Publish is clicked.
     *
     * Publishes the reply.
     */
    _onPublishClicked: function() {
        this.model.publish({
            error: function(model, xhr) {
                this.model.trigger('publishError', xhr.errorText);
            }
        }, this);
    },

    /*
     * Handler for when Discard is clicked.
     *
     * Discards the reply.
     */
    _onDiscardClicked: function() {
        this.model.destroy();
    }
});
