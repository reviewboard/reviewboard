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

    loadErrorTemplate: _.template([
        '<div class="error">',
        ' <p><%- errorLoadingText %></p>',
        ' <p class="error-text">',
        '  <% _.each(errorLines, function(line) { %><%- line %><br /><% }); %>',
        ' </p>',
        ' <p>',
        '  <%- temporaryFailureText %>',
        '  <a href="#" id="reload_<%- reloadID %>"><%- tryAgainText %></a>',
        ' </p>',
        '</div>'
    ].join('')),

    events: {
        'click #reload_branches': '_loadBranches',
        'click #reload_commits': '_loadCommits'
    },

    /*
     * Initialize the view.
     */
    initialize: function() {
        var model = this.model,
            repository = model.get('repository'),
            branches = repository.branches;

        this._$error = null;

        // Set up the branch selector and bind it to the "branch" attribute
        this._branchesView = new RB.BranchesView({
            collection: branches
        });
        this._branchesView.on('selected', function(branch) {
            model.set('branch', branch);
        }, this);

        this.listenTo(model, 'change:branch', this._onBranchChanged);

        if (!branches.loaded) {
            this._loadBranches();
        }
    },

    /*
     * Render the view.
     */
    render: function() {
        var $branch = $('<div/>')
            .addClass('branches section-header');

        this._rendered = true;

        $branch
            .append($('<span/>')
                .text(gettext('Create from an existing commit on:')))
            .append(this._branchesView.render().el)
            .appendTo(this.$el);

        if (this._commitsView) {
            this.$el.append(this._commitsView.render().el);
        }

        return this;
    },

    /*
     * Loads the list of branches from the repository.
     *
     * If there's an error loading the branches, the branches selector and
     * commits list will be hidden, and an error will be displayed along
     * with the message from the server. The user will have the ability to
     * try again.
     */
    _loadBranches: function() {
        var branches = this.model.get('repository').branches;

        this._clearLoadError();

        branches.fetch({
            success: function() {
                branches.loaded = true;

                this._branchesView.$el.show();

                if (this._commitsView) {
                    this._commitsView.$el.show();
                }
            },
            error: function(collection, xhr) {
                this._branchesView.$el.hide();

                if (this._commitsView) {
                    this._commitsView.$el.hide();
                }

                this._showLoadError('branches', xhr);
            }
        }, this);
    },

    /*
     * Loads the list of commits from the repository.
     *
     * If there's an error loading the commits, the commits list will be
     * hidden, and an error will be displayed along with the message from
     * the server. The user will have the ability to try again.
     */
    _loadCommits: function() {
        this._clearLoadError();

        this._commitsCollection.fetch({
            success: function() {
                this._commitsView.$el.show();
            },
            error: function(collection, xhr) {
                this._commitsView.$el.hide();
                this._showLoadError('commits', xhr);
            }
        }, this);
    },

    /*
     * Clears any displayed error message.
     */
    _clearLoadError: function() {
        if (this._$error) {
            this._$error.remove();
            this._$error = null;
        }
    },

    /*
     * Shows an error message indicating a load failure.
     *
     * The message from the server will be displayed along with some
     * helpful text and a link for trying the request again.
     */
    _showLoadError: function(reloadID, xhr) {
        this._clearLoadError();

        this._$error = $(this.loadErrorTemplate({
                errorLoadingText: gettext('There was an error loading information from this repository:'),
                temporaryFailureText: gettext('This may be a temporary failure.'),
                tryAgainText: gettext('Try again'),
                errorLines: xhr.errorText.split('\n'),
                reloadID: reloadID
            }))
            .appendTo(this.$el);
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
            this.model.get('repository').getCommits({
                branch: branch.id,
                start: branch.get('commit')
            });
        this.listenTo(this._commitsCollection, 'create', this._onCreateReviewRequest);

        this._commitsView = new RB.CommitsView({
            collection: this._commitsCollection
        });
        if (this._rendered) {
            this.$el.append(this._commitsView.render().el);
        }

        this._loadCommits();
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
            repository: repository.id,
            localSitePrefix: repository.get('localSitePrefix')
        });

        reviewRequest.createFromCommit({
            commitID: commit.id,
            success: function() {
                window.location = reviewRequest.get('reviewURL');
            },
            error: function(model, xhr) {
                this._commitsView.setPending(null);
                this._createPending = false;
                alert(xhr.errorText);
            }
        }, this);
    }
});
