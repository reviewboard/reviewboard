/**
 * Displays all the initial status updates.
 *
 * Initial status updates are those which do not correspond to a change
 * description (i.e. those posted against the first revision of a diff or any
 * file attachments that were present when the review request was first
 * published).
 */
RB.InitialStatusUpdatesBoxView = RB.CollapsableBoxView.extend({
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
     *
     *     reviews (array of RB.Review):
     *         Models for each review.
     */
    initialize(options) {
        RB.CollapsableBoxView.prototype.initialize.call(this, options);

        this._reviews = options.reviews;
        this._reviewViews = this._reviews.map(
            review => new RB.ReviewView({
                el: this.$(`#review${review.id}`),
                model: review,
            }));
    },

    /**
     * Render the box.
     *
     * Returns:
     *     RB.InitialStatusUpdatesBoxView:
     *     This object, for chaining.
     */
    render() {
        RB.CollapsableBoxView.prototype.render.call(this);

        this._reviewViews.forEach(view => view.render());

        return this;
    },
});
