(function() {


const commentTypeToIDPrefix = {
    diff: '',
    file: 'f',
    screenshot: 's',
};


/**
 * Manages the review request page.
 *
 * This manages all the reviews on the page, diff fragment loading, and
 * other functionality needed for the main review request page.
 */
RB.ReviewRequestPage.ReviewRequestPageView = RB.ReviewablePageView.extend({
    events: _.extend({
        'click #collapse-all': '_onCollapseAllClicked',
        'click #expand-all': '_onExpandAllClicked',
    }, RB.ReviewablePageView.prototype.events),

    /**
     * Initialize the page.
     */
    initialize() {
        RB.ReviewablePageView.prototype.initialize.apply(this, arguments);

        this._entryViews = [];
        this._entryViewsByID = {};
        this._rendered = false;
        this._issueSummaryTableView = null;

        const reviewRequest = this.model.get('reviewRequest');

        this.diffFragmentQueue = new RB.DiffFragmentQueueView({
            reviewRequestPath: reviewRequest.get('reviewURL'),
            containerPrefix: 'comment_container',
            queueName: 'diff_fragments',
            el: document.getElementById('content'),
            diffFragmentViewOptions: {
                collapsible: true,
            },
        });

        /*
         * Listen for when a new set of updates have been processed. After
         * processing, this will attempt to load any new diff fragments that
         * may have been added in any updated views.
         */
        this.listenTo(this.model, 'updatesProcessed',
                      () => this.diffFragmentQueue.loadFragments());

        /*
         * Listen for updates to any entries on the page. When updated,
         * we'll store the collapse state on the entry so we can re-apply it
         * after. We listen to the other events that are part of the update so
         * we can update the DOM and restore state at the correct time.
         */
        this.listenTo(this.model, 'applyingUpdate:entry', (metadata, html) => {
            const entryID = metadata.entryID;
            const entryView = this._entryViewsByID[entryID];
            const collapsed = entryView.isCollapsed();

            this._onApplyingUpdate(entryView, metadata);

            this.listenToOnce(
                this.model,
                `appliedModelUpdate:entry:${entryID}`,
                (metadata, html) => this._reloadView(entryView, html));

            this.listenToOnce(
                this.model,
                `appliedUpdate:entry:${entryID}`,
                metadata => {
                    this._onAppliedUpdate(entryView, metadata);

                    if (collapsed) {
                        entryView.collapse();
                    } else {
                        entryView.expand();
                    }
                });
        });
    },

    /**
     * Render the page.
     *
     * Returns:
     *     RB.ReviewRequestPage.ReviewRequestPageView:
     *     This object, for chaining.
     */
    render() {
        RB.ReviewablePageView.prototype.render.call(this);

        /*
         * Render each of the entries on the page.
         */
        this._entryViews.forEach(entryView => entryView.render());

        /*
         * Navigate to the right anchor on the page, if there's a valid hash
         * in the URL. We'll also do this whenever it changes, if the browser
         * supports this.
         */
        this._onHashChanged();

        if ('onhashchange' in window) {
            window.onhashchange = this._onHashChanged.bind(this);
        }

        /*
         * Load all the diff fragments queued up in each review.
         */
        this.diffFragmentQueue.loadFragments();

        /*
         * Set up the Issue Summary Table and begin listening for related
         * events.
         */
        this._issueSummaryTableView =
            new RB.ReviewRequestPage.IssueSummaryTableView({
                el: $('#issue-summary'),
                model: this.model.commentIssueManager,
            });

        this._issueSummaryTableView.render();

        this.listenTo(this._issueSummaryTableView,
                      'issueClicked',
                      this._onIssueClicked);
        this.listenTo(this.model, 'appliedUpdate:issue-summary-table',
                      (metadata, html) => {
            this._reloadView(this._issueSummaryTableView, html);
        });

        this._rendered = true;

        return this;
    },

    /**
     * Add a new entry and view to the page.
     *
     * Args:
     *     entryView (RB.ReviewRequestPage.EntryView):
     *         The new entry's view to add.
     */
    addEntryView(entryView) {
        const entry = entryView.model;

        this._entryViews.push(entryView);
        this._entryViewsByID[entry.id] = entryView;
        this.model.addEntry(entry);

        if (this._rendered) {
            entryView.render();
        }
    },

    /**
     * Queue a diff fragment for loading.
     *
     * The diff fragment will be part of a comment made on a diff.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment to load the diff fragment for.
     *
     *     key (string):
     *         Either a single filediff ID, or a pair (filediff ID and
     *         interfilediff ID) separated by a hyphen.
     *
     *     onFragmentRendered (function, optional):
     *         Optional callback for when the view for the fragment has
     *         rendered. Contains the view as a parameter.
     */
    queueLoadDiff(commentID, key, onFragmentRendered) {
        this.diffFragmentQueue.queueLoad(commentID, key, onFragmentRendered);
    },

    /**
     * Open a comment editor for the given comment.
     *
     * This is used when clicking Reply from a comment dialog on another
     * page.
     *
     * Args:
     *     contextType (string):
     *         The type of object being edited (such as ``body_top`` or
     *         ``diff_comments``)
     *
     *     contextID (number, optional):
     *         The ID of the comment being edited, if appropriate.
     */
    openCommentEditor(contextType, contextID) {
        for (let i = 0; i < this._entryViews.length; i++) {
            const entryView = this._entryViews[i];
            const reviewReplyEditorView = (
                _.isFunction(entryView.getReviewReplyEditorView)
                ? entryView.getReviewReplyEditorView(contextType, contextID)
                : null);

            if (reviewReplyEditorView) {
                reviewReplyEditorView.openCommentEditor();
                break;
            }
        }
    },

    /**
     * Reload the HTML for a view.
     *
     * This will replace the view's element with a new one consisting of the
     * provided HTML. This is done in response to an update from the server.
     *
     * Args:
     *     view (Backbone.View):
     *         The view to set new HTML for.
     *
     *     html (string):
     *         The new HTML to set.
     */
    _reloadView(view, html) {
        const $oldEl = view.$el;
        const $newEl = $(html);

        view.setElement($newEl);
        $oldEl.replaceWith($newEl);
        view.render();
    },

    /**
     * Handler for when a new update is being applied to a view.
     *
     * This will call the ``beforeApplyUpdate`` method on the view, if it
     * exists. This is called before the model's equivalent handler.
     *
     * Args:
     *     view (Backbone.View):
     *         The view being updated.
     *
     *     metadata (object):
     *         The metadata set in the update.
     */
    _onApplyingUpdate(view, metadata) {
        if (view && _.isFunction(view.beforeApplyUpdate)) {
            view.beforeApplyUpdate(metadata);
        }
    },

    /**
     * Handler for when a new update has been applied to a view.
     *
     * This will call the ``afterApplyUpdate`` method on the view, if it
     * exists. This is called after the model's equivalent handler.
     *
     * Args:
     *     view (Backbone.View):
     *         The view that has been updated.
     *
     *     metadata (object):
     *         The metadata set in the update.
     */
    _onAppliedUpdate(view, metadata) {
        if (view && _.isFunction(view.afterApplyUpdate)) {
            view.afterApplyUpdate(metadata);
        }
    },

    /**
     * Handler for when the location hash changes.
     *
     * This will attempt to locate a proper anchor point for the given
     * hash, if one is provided, and scroll down to that anchor. The
     * scrolling will take any docked floating banners (the review draft,
     * specifically) into consideration to ensure the entirety of the comment
     * is shown on-screen.
     */
    _onHashChanged() {
        const hash = RB.getLocationHash();
        let selector = null;

        if (hash !== '') {
            if (hash.includes('comment')) {
                selector = `a[name=${hash}]`;
            } else {
                selector = `#${hash}`;
            }
        }

        if (!selector) {
            return;
        }

        /*
         * If trying to link to some anchor in some entry, we'll expand the
         * first entry containing that anchor.
         */
        for (let i = 0; i < this._entryViews.length; i++) {
            const entryView = this._entryViews[i];
            const $anchor = entryView.$(selector);

            if ($anchor.length > 0) {
                /*
                 * We found the entry containing the specified anchor.
                 * Expand it and stop searching the rest of the entries.
                 */
                entryView.expand();

                /*
                 * Scroll down to the particular anchor, now that the entry
                 * is expanded.
                 */
                RB.scrollManager.scrollToElement($anchor);
                break;
            }
        }
    },

    /**
     * Handle a press on the Collapse All button.
     *
     * Collapses each entry.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onCollapseAllClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._entryViews.forEach(entryView => entryView.collapse());
    },

    /**
     * Handle a press on the Expand All button.
     *
     * Expands each entry.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onExpandAllClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._entryViews.forEach(entryView => entryView.expand());
    },

    /**
     * Handler for when an issue in the issue summary table is clicked.
     *
     * This will expand the review entry that contains the comment for the
     * issue, and navigate to the comment.
     *
     * Args:
     *     params (object):
     *         Parameters passed to the event handler.
     */
    _onIssueClicked(params) {
        const prefix = commentTypeToIDPrefix[params.commentType];
        const selector = `#${prefix}comment${params.commentID}`;

        this._entryViews.forEach(entryView => {
            if (entryView.$el.find(selector).length > 0) {
                entryView.expand();
            }
        });

        window.location = params.commentURL;
    },
});


})();
