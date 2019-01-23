/**
 * A banner that represents a pending reply to a review.
 *
 * The banner offers actions for publishing and discarding the review.
 */
RB.ReviewRequestPage.ReviewReplyDraftBannerView = RB.FloatingBannerView.extend({
    className: 'banner',

    template: _.template(dedent`
        <h1><%- draftText %></h1>
        <p><%- reminderText %></p>
        <span class="banner-actions">
         <input type="button" value="<%- publishText %>"
                class="publish-button" />
         <input type="button" value="<%- discardText %>"
                class="discard-button" />
        </span>
        <% if (showSendEmail) { %>
         <label>
          <input type="checkbox" class="send-email" checked />
          <%- sendEmailText %>
        </label>
        <% } %>
    `),

    events: {
        'click .publish-button': '_onPublishClicked',
        'click .discard-button': '_onDiscardClicked',
    },

    /**
     * Render the banner.
     *
     * Returns:
     *     RB.ReviewRequestPage.ReviewReplyDraftBannerView:
     *     This object, for chaining.
     */
    render() {
        RB.FloatingBannerView.prototype.render.call(this);

        const reviewRequestEditor = this.options.reviewRequestEditor;

        this.$el.html(this.template({
            draftText: gettext('This reply is a draft.'),
            reminderText: gettext('Be sure to publish when finished.'),
            publishText: gettext('Publish'),
            discardText: gettext('Discard'),
            sendEmailText: gettext('Send E-Mail'),
            showSendEmail: reviewRequestEditor.get('showSendEmail'),
        }));

        this.listenTo(this.model, 'saving destroying',
                      () => this.$('input').prop('disabled', true));
        this.listenTo(this.model, 'saved',
                      () => this.$('input').prop('disabled', false));
        this.listenTo(this.model, 'publishError',
                      errorText => alert(errorText));

        return this;
    },

    /**
     * Handler for when Publish is clicked.
     *
     * Publishes the reply.
     */
    _onPublishClicked() {
        const $sendEmail = this.$('.send-email');

        this.model.publish({
            trivial: $sendEmail.length === 1 && !$sendEmail.is(':checked'),
        }, this);
    },

    /**
     * Handler for when Discard is clicked.
     *
     * Discards the reply.
     */
    _onDiscardClicked() {
        this.model.destroy();
    },
});
