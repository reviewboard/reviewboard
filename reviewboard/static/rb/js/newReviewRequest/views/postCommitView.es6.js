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
        'click #reload_branches': '_loadBranches',
        'click #reload_commits': '_loadCommits',
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
     * Load the list of branches from the repository.
     *
     * If there's an error loading the branches, the branches selector and
     * commits list will be hidden, and an error will be displayed along
     * with the message from the server. The user will have the ability to
     * try again.
     */
    _loadBranches() {
        this._clearLoadError();

        const branches = this.model.get('repository').branches;

        branches.fetch({
            success: () => {
                branches.loaded = true;

                this._branchesView.$el.show();

                if (this._commitsView) {
                    this._commitsView.$el.show();
                }
            },
            error: (collection, xhr) => {
                this._branchesView.$el.hide();

                if (this._commitsView) {
                    this._commitsView.$el.hide();
                }

                this._showLoadError('branches', xhr);
            },
        });
    },

    /**
     * Load the list of commits from the repository.
     *
     * If there's an error loading the commits, the commits list will be
     * hidden, and an error will be displayed along with the message from
     * the server. The user will have the ability to try again.
     */
    _loadCommits() {
        this._clearLoadError();

        this._commitsCollection.fetch({
            success: () => {
                this._commitsView.$el.show();
            },
            error: (collection, xhr) => {
                this._commitsView.$el.hide();
                this._showLoadError('commits', xhr);
            },
        });
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
     *     xhr (jqXHR):
     *         The HTTP Request object.
     */
    _showLoadError(reloadID, xhr) {
        this._clearLoadError();

        this._$error = $(this.loadErrorTemplate({
                errorLoadingText: gettext('There was an error loading information from this repository:'),
                temporaryFailureText: gettext('This may be a temporary failure.'),
                tryAgainText: gettext('Try again'),
                errorLines: xhr.errorText.split('\n'),
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
    _onCreateReviewRequest(commit) {
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

        reviewRequest.createFromCommit({
            commitID: commit.id,
            success: () => {
                window.location = reviewRequest.get('reviewURL');
            },
            error: (model, xhr) => {
                this._commitsView.setPending(null);
                this._createPending = false;
                alert(xhr.errorText);
            },
        });
    },
});
