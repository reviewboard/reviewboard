/*
 * A view orchestrating post-commit review request creation.
 *
 * This brings together the BranchesView and CommitsView to provide a UI for
 * letting people browse through the committed revisions in the repository. When
 * the user clicks on one of the commits, it will create a new review request
 * using that commit's ID.
 */
RB.PostCommitView = Backbone.View.extend({
    className: 'post-commit',

    /*
     * Initialize the view.
     */
    initialize: function() {
        var model = this.model,
            repository = model.get('repository'),
            branches = repository.branches;

        // Set up the branch selector and bind it to the "branch" attribute
        if (!branches.loaded) {
            branches.fetch({
                success: function() {
                    branches.loaded = true;
                }
            });
        }

        this._branchesView = new RB.BranchesView({
            collection: branches
        });
        this._branchesView.on('selected', function(branch) {
            model.set('branch', branch);
        }, this);

        this.listenTo(model, 'change:branch', this._onBranchChanged);
    },

    /*
     * Render the view.
     */
    render: function() {
        var $branch = $('<div/>')
            .addClass('branches section-header');

        this._rendered = true;

        $branch
            .append(gettext('New Review Request for Committed Change:'))
            .append(this._branchesView.render().el)
            .appendTo(this.$el);

        if (this._commitsView) {
            this.$el.append(this._commitsView.render().el);
        }

        return this;
    },

    /*
     * Callback for when the user chooses a different branch.
     *
     * Fetches a new list of commits starting from the tip of the selected
     * branch.
     */
    _onBranchChanged: function(model, branch) {
        if (this._commitsView) {
            this.stopListening(this._commitsCollection);
            this._commitsView.remove();
        }

        this._commitsCollection =
            this.model.get('repository').getCommits(branch.get('commit'));
        this._commitsCollection.fetch();
        this.listenTo(this._commitsCollection, 'create', this._onCreateReviewRequest);

        this._commitsView = new RB.CommitsView({
            collection: this._commitsCollection
        });
        if (this._rendered) {
            this.$el.append(this._commitsView.render().el);
        }
    },

    /*
     * Callback for when a commit is selected.
     *
     * Creates a new review request with the given commit ID and redirects the
     * browser to it.
     */
    _onCreateReviewRequest: function(commit) {
        var repository = this.model.get('repository'),
            reviewRequest;

        if (this._createPending) {
            // Do nothing
            return;
        }

        this._createPending = true;
        this._commitsView.setPending(commit);

        reviewRequest = new RB.ReviewRequest({
            commitID: commit.get('id'),
            repository: repository.get('id')
        });

        reviewRequest.save({
            success: function() {
                window.location = reviewRequest.get('reviewURL');
            },
            error: function() {
                // TODO: handle errors
            }
        });
    }
});
