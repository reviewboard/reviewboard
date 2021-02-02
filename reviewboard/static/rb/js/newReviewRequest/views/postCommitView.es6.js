/**
 * A view orchestrating post-commit review request creation.
 *
 * This brings together the BranchesView and CommitsView to provide a UI for
 * letting people browse through the committed revisions in the repository. When
 * the user clicks on one of the commits, it will create a new review request
 * using that commit's ID.
 */
RB.PostCommitView = Backbone.View.extend({
    className: 'post-commit',

    loadErrorTemplate: _.template(dedent`
        <div class="error">
         <p><%- errorLoadingText %></p>
         <p class="error-text">
          <% _.each(errorLines, function(line) { %><%- line %><br /><% }); %>
         </p>
         <p>
          <%- temporaryFailureText %>
          <a href="#" id="reload_<%- reloadID %>"><%- tryAgainText %></a>
         </p>
        </div>
    `),

    events: {
        'click #reload_branches': '_onReloadBranchesClicked',
        'click #reload_commits': '_onReloadCommitsClicked',
    },

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
        const model = this.model;
        const repository = model.get('repository');
        const branches = repository.branches;

        this._$scrollContainer = options.$scrollContainer;
        this._$error = null;

        // Set up the branch selector and bind it to the "branch" attribute
        this._branchesView = new RB.BranchesView({
            collection: branches,
        });
        this._branchesView.on('selected',
                              branch => model.set('branch', branch));

        this.listenTo(model, 'change:branch', this._onBranchChanged);

        if (!branches.loaded) {
            this._loadBranches();
        }
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.PostCommitView:
     *     This object, for chaining.
     */
    render() {
        this._rendered = true;

        $('<div/>')
            .addClass('branches section-header')
            .append($('<span/>')
                .text(gettext('Create from an existing commit on:')))
            .append(this._branchesView.render().el)
            .appendTo(this.$el);

        if (this._commitsView) {
            this.$el.append(this._commitsView.render().el);
        }

        return this;
    },

    /**
     * Callback for when the user clicked on the reload branches button.
     *
     * This exists for use with unit test spies.
     */
    _onReloadBranchesClicked() {
        this._loadBranches();
    },

    /**
     * Callback for when the user clicked on the reload commits button.
     *
     * This exists for use with unit test spies.
     */
    _onReloadCommitsClicked() {
        this._loadCommits();
    },

    /**
     * Load the list of branches from the repository.
     *
     * If there's an error loading the branches, the branches selector and
     * commits list will be hidden, and an error will be displayed along
     * with the message from the server. The user will have the ability to
     * try again.
     *
     * Version Changed:
     *     5.0:
     *     The promise return value was added.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async _loadBranches() {
        this._clearLoadError();

        const branches = this.model.get('repository').branches;

        try {
            await branches.fetch();
        } catch (err) {
            this._branchesView.$el.hide();
            this._commitsView?.$el?.hide();
            this._showLoadError('branches', err.message);
            return;
        }

        branches.loaded = true;
        this._branchesView.$el.show();
        this._commitsView?.$el?.hide();
    },

    /**
     * Load the list of commits from the repository.
     *
     * If there's an error loading the commits, the commits list will be
     * hidden, and an error will be displayed along with the message from
     * the server. The user will have the ability to try again.
     *
     * Version Changed:
     *     5.0:
     *     The promise return value was added.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async _loadCommits() {
        this._clearLoadError();

        try {
            await this._commitsCollection.fetch();
        } catch(err) {
            this._commitsView.$el.hide();
            this._showLoadError('commits', err.message);
            return;
        }

        this._commitsView.$el.show();
        this._commitsView.checkFetchNext();
    },

    /**
     * Clear any displayed error message.
     */
    _clearLoadError() {
        if (this._$error) {
            this._$error.remove();
            this._$error = null;
        }
    },

    /**
     * Show an error message indicating a load failure.
     *
     * The message from the server will be displayed along with some
     * helpful text and a link for trying the request again.
     *
     * Args:
     *     reloadID (string):
     *         An ID to use for the reload link element.
     *
     *     err (string):
     *         The error text.
     */
    _showLoadError(reloadID, err) {
        this._clearLoadError();

        this._$error = $(this.loadErrorTemplate({
                errorLoadingText: gettext('There was an error loading information from this repository:'),
                temporaryFailureText: gettext('This may be a temporary failure.'),
                tryAgainText: gettext('Try again'),
                errorLines: err.split('\n'),
                reloadID: reloadID,
            }))
            .appendTo(this.$el);
    },

    /**
     * Callback for when the user chooses a different branch.
     *
     * Fetches a new list of commits starting from the tip of the selected
     * branch.
     *
     * Args:
     *     model (RB.PostCommitModel):
     *         The data model.
     *
     *     branch (RB.RepositoryBranch):
     *         The selected branch.
     */
    _onBranchChanged(model, branch) {
        if (this._commitsView) {
            this.stopListening(this._commitsCollection);
            this._commitsView.remove();
        }

        this._commitsCollection =
            this.model.get('repository').getCommits({
                branch: branch.id,
                start: branch.get('commit'),
            });
        this.listenTo(this._commitsCollection, 'create',
                      this._onCreateReviewRequest);

        this._commitsView = new RB.CommitsView({
            collection: this._commitsCollection,
            $scrollContainer: this._$scrollContainer,
        });
        this.listenTo(this._commitsView, 'loadError', xhr => {
            this._showLoadError('commits', xhr);
        });

        if (this._rendered) {
            this.$el.append(this._commitsView.render().el);
        }

        this._loadCommits();
    },

    /**
     * Callback for when a commit is selected.
     *
     * Creates a new review request with the given commit ID and redirects the
     * browser to it.
     *
     * Args:
     *     commit (RB.RepositoryCommit):
     *         The selected commit.
     */
    async _onCreateReviewRequest(commit) {
        if (this._createPending) {
            // Do nothing
            return;
        }

        this._createPending = true;
        this._commitsView.setPending(commit);

        const repository = this.model.get('repository');
        const reviewRequest = new RB.ReviewRequest({
            repository: repository.id,
            localSitePrefix: repository.get('localSitePrefix')
        });

        try {
            await reviewRequest.createFromCommit(commit.id);
        } catch (err) {
            this._commitsView.setPending(null);
            this._createPending = false;
            alert(err.message);
            return;
        }

        this._navigateTo(reviewRequest.get('reviewURL'));
    },

    /**
     * Navigate to the given URL.
     *
     * This exists so it can be overridden by unit tests.
     *
     * Args:
     *     url (string):
     *         The URL to navigate to.
     */
    _navigateTo(url) {
        window.location = url;
    },
});
