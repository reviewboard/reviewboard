{


const ParentView = RB.ReviewRequestPage.EntryView;


/**
 * Displays all the initial status updates.
 *
 * Initial status updates are those which do not correspond to a change
 * description (i.e. those posted against the first revision of a diff or any
 * file attachments that were present when the review request was first
 * published).
 */
RB.ReviewRequestPage.InitialStatusUpdatesEntryView = ParentView.extend({
    /**
     * Initialize the view.
     */
    initialize() {
        ParentView.prototype.initialize.call(this);

        this._reviews = this.model.get('reviews');
        this._reviewViews = this._reviews.map(review => {
            const $reviewEl = this.$(`#review${review.id}`);

            return new RB.ReviewRequestPage.ReviewView({
                el: $reviewEl,
                model: review,
                entryModel: this.model,
                $bannerFloatContainer: $reviewEl,
                $bannerParent: $reviewEl.children('.banners'),
                bannerNoFloatContainerClass: 'collapsed',
            });
        });
    },

    /**
     * Render the box.
     *
     * Returns:
     *     RB.ReviewRequestPage.InitialStatusUpdatesEntryView:
     *     This object, for chaining.
     */
    render() {
        ParentView.prototype.render.call(this);

        this._reviewViews.forEach(view => view.render());

        return this;
    },
});


}
