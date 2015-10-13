(function() {


var FilesOnlyPreCommitModel,
    FilesOnlyPreCommitView;


/*
 * A simple model for creating file-attachment only review requests.
 */
FilesOnlyPreCommitModel = Backbone.Model.extend({
    defaults: _.defaults({
        repository: null
    })
});


/*
 * A simple view for creating file-attachment only review requests.
 */
FilesOnlyPreCommitView = Backbone.View.extend({
    className: 'files-only',

    template: _.template([
        '<p><%- description %></p>',
        '<input type="submit" class="primary large" id="files-only-create"',
        '       value="<%- buttonText %>" />'
    ].join('')),

    events: {
        'click #files-only-create': '_onCreateClicked'
    },

    /*
     * Render the view.
     */
    render: function() {
        this.$el.html(this.template({
            description: gettext('You won\'t be able to add any diffs to this review request. The review request will only be usable for reviewing graphics, screenshots and file attachments.'),
            buttonText: gettext('Create Review Request')
        }));
        return this;
    },

    /*
     * Callback for when the "Create Review Request" button is clicked.
     *
     * Creates a review request with the given localSitePrefix and nothing else,
     * and redirects the browser to it.
     */
    _onCreateClicked: function() {
        var repository = this.model.get('repository'),
            reviewRequest = new RB.ReviewRequest({
                localSitePrefix: repository.get('localSitePrefix')
            });

        reviewRequest.save({
            success: function() {
                window.location = reviewRequest.get('reviewURL');
            },

            error: function() {
                // TODO: handle errors
            }
        });

        return false;
    }
});


/*
 * The view for creating new review requests.
 *
 * This orchestrates several other objects to guide users through creating file
 * attachment only, pre-commit, or post-commit review requests.
 */
RB.NewReviewRequestView = Backbone.View.extend({
    el: '#new-review-request',

    template: _.template([
        '<a href="#" class="show-repositories">',
        ' <span class="fa fa-chevron-left"></span>',
        ' <%- repositoriesLabel %>',
        '</a>',
        '<div class="new-review-request-container">',
        ' <div class="main">',
        '  <div class="hint"><%- hint %></div>',
        ' </div>',
        '</div>'
    ].join('')),

    events: {
        'click .show-repositories': '_onShowRepositoriesClicked'
    },

    /*
     * Initialize the view.
     */
    initialize: function() {
        this._repositorySelectionView = new RB.RepositorySelectionView({
            collection: this.model.get('repositories')
        });
        this.listenTo(this._repositorySelectionView, 'selected',
                      this._onRepositorySelected);

        $(window).resize(_.bind(this._onResize, this));
    },

    /*
     * Render the view.
     */
    render: function() {
        var repositories = this.model.get('repositories').models;

        this._rendered = true;

        this.$el.html(this.template({
            hint: gettext('Select a repository'),
            repositoriesLabel: gettext('Repositories')
        }));
        this._$sidebar = $('#page_sidebar');
        this._$content = this.$('.main');
        this._$hint = this.$('.hint');

        this._$sidebar.append(this._repositorySelectionView.el);
        this._repositorySelectionView.render();

        if (this._preCommitView) {
            this._$hint.hide();
            this._$content.append(this._preCommitView.render().el);
        }
        if (this._postCommitView) {
            this._$hint.hide();
            this._$content.append(this._postCommitView.render().el);
        }

        this.$el.show();
        this._onResize();

        /*
         * If the only two options are the "None - File attachments only"
         * pseudo-repository and one real one, pre-select the real one to speed
         * up the 80% case. Otherwise, we'll leave it at the "Select a
         * repository" screen.
         */
        if (repositories.length === 2) {
            repositories[1].trigger('selected', repositories[1]);
        }

        return this;
    },

    /*
     * Callback for when the window is resized. Recomputes the size of the view
     * to fit nicely on screen.
     */
    _onResize: function() {
        var $window,
            windowWidth,
            windowHeight,
            elTop,
            height;

        if (this._rendered) {
            $window = $(window);
            windowWidth = $window.width();
            windowHeight = $window.height();
            elTop = this.$el.offset().top;
            height = windowHeight - elTop - 14;

            this.$el.height(height);

            // Adjust for the "< Repositories" link on mobile.
            height -= this._$content.position().top;
            this._$content.height(height);
        }
    },

    /*
     * Callback for when a repository is selected.
     *
     * If the "Files Only" entry is selected, this shows the special
     * FilesOnlyPreCommitView in the right-hand pane.
     *
     * If a repository that supports fetching committed revisions is selected,
     * this will show both the pre-commit and post-commit UIs stacked
     * vertically. If the repository only supports pre-commit, only the
     * pre-commit UI is shown.
     */
    _onRepositorySelected: function(repository) {
        if (this._preCommitView) {
            this._preCommitView.remove();
            this._preCommitView = null;
        }

        if (this._postCommitView) {
            this._postCommitView.remove();
            this._postCommitView = null;
        }

        this.model.set('repository', repository);

        if (repository === null) {
            return;
        }

        $(document.body).removeClass('mobile-show-page-sidebar');

        if (repository.get('filesOnly')) {
            this._preCommitView = new FilesOnlyPreCommitView({
                model: new FilesOnlyPreCommitModel({
                    repository: repository
                })
            });
        } else {
            this._preCommitView = new RB.PreCommitView({
                model: new RB.UploadDiffModel({
                    repository: repository
                })
            });

            if (repository.get('supportsPostCommit')) {
                this._postCommitView = new RB.PostCommitView({
                    model: new RB.PostCommitModel({
                        repository: repository
                    })
                });
            }
        }

        if (this._rendered) {
            this._$hint.hide();
            this._$content.append(this._preCommitView.render().el);

            if (this._postCommitView) {
                this._$content.append(this._postCommitView.render().el);
            }
        }
    },

    /*
     * Handler for when the mobile-only Show Repositories link is clicked.
     *
     * Sets the page to slide back to the sidebar listing repositories.
     */
    _onShowRepositoriesClicked: function() {
        this._repositorySelectionView.unselect();
        $(document.body).addClass('mobile-show-page-sidebar');
    }
});


})();
