/**
 * A view that lists a series of commits.
 *
 * This is intended to be used for creating new review requests from committed
 * revisions. The containing view can call setPending/cancelPending to ask an
 * individual commit to show a spinner.
 */
RB.CommitsView = RB.CollectionView.extend({
    className: 'commits',
    itemViewType: RB.CommitView,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     $scrollContainer (jQuery):
     *         The parent container handling all content scrolling.
     */
    initialize(options) {
        RB.CollectionView.prototype.initialize.call(this, options);

        this._$scrollContainer = options.$scrollContainer;
    },

    /**
     * Render the view.
     *
     * Delegates the hard work to the parent class, and sets up the scroll
     * handler.
     *
     * Returns:
     *     RB.CommitsView:
     *     This object, for chaining.
     */
    render() {
        RB.CollectionView.prototype.render.call(this);

        this._$scrollContainer.scroll(this._onScroll.bind(this));

        return this;
    },

    /**
     * Set a given commit "pending".
     *
     * This is used while creating a new review request, and will ask the
     * correct commit view to show a spinner.
     *
     * Args:
     *     commit (RB.RepositoryCommit):
     *         The selected commit.
     */
    setPending(commit) {
        this.views.forEach(view => {
            if (view.model === commit) {
                view.showProgress();
            } else {
                view.cancelProgress();
            }
        });
    },

    /**
     * Cancel the pending state on all commits.
     */
    cancelPending() {
        this.views.forEach(view => view.cancelProgress());
    },

    /**
     * Handler for a scroll event.
     *
     * If we get within 50px of the bottom, try to fetch the next page of
     * commits.
     *
     * Args:
     *     ev (Event):
     *         The scroll event.
     */
    _onScroll(ev) {
        const scrollThresholdPx = 50;

        if ((ev.target.scrollTop + ev.target.offsetHeight) >
                (ev.target.scrollHeight - scrollThresholdPx)) {
            this.collection.fetchNext();
        }
    },
});
