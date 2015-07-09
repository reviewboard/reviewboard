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
        '</span>',
        '<% if (showSendEmail) { %>',
        ' <label>',
        '  <input type="checkbox" class="send-email" checked />',
        '  <%- sendEmailText %>',
        '</label>',
        '<% } %>'
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
            discardText: gettext('Discard'),
            sendEmailText: gettext('Send E-Mail'),
            showSendEmail: this.options.showSendEmail
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
        var $sendEmail = this.$('.send-email');

        this.model.publish({
            trivial: $sendEmail.length === 1 && !$sendEmail.is(':checked')
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
