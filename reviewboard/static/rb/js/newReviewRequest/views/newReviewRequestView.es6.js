(function() {


/**
 * A simple model for creating file-attachment only review requests.
 *
 * Model Attributes:
 *     repository (RB.Repository):
 *         The associated repository (always ``null``).
 */
const FilesOnlyPreCommitModel = Backbone.Model.extend({
    defaults: _.defaults({
        repository: null,
    }),
});


/**
 * A simple view for creating file-attachment only review requests.
 */
const FilesOnlyPreCommitView = Backbone.View.extend({
    className: 'files-only',

    template: _.template(dedent`
        <p><%- description %></p>
        <input type="submit" class="primary large" id="files-only-create"
               value="<%- buttonText %>" />
    `),

    events: {
        'click #files-only-create': '_onCreateClicked',
    },

    /**
     * Render the view.
     *
     * Returns:
     *     FilesOnlyPreCommitView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template({
            description: gettext('You won\'t be able to add any diffs to this review request. The review request will only be usable for reviewing graphics, screenshots and file attachments.'),
            buttonText: gettext('Create Review Request'),
        }));

        return this;
    },

    /**
     * Callback for when the "Create Review Request" button is clicked.
     *
     * Creates a review request with the given localSitePrefix and nothing else,
     * and redirects the browser to it.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onCreateClicked(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const repository = this.model.get('repository');
        const reviewRequest = new RB.ReviewRequest({
            localSitePrefix: repository.get('localSitePrefix')
        });

        reviewRequest.save({
            success: () => {
                window.location = reviewRequest.get('reviewURL');
            },
            error: () => {
                // TODO: handle errors
            },
        });
    },
});


/**
 * The view for creating new review requests.
 *
 * This orchestrates several other objects to guide users through creating file
 * attachment only, pre-commit, or post-commit review requests.
 */
RB.NewReviewRequestView = RB.PageView.extend({
    el: '#new-review-request',

    template: _.template(dedent`
        <div class="rb-c-new-review-request">
         <div class="rb-c-sidebar -no-icons"></div>
         <div class="rb-c-new-review-request__repo-pane">
          <a href="#" class="rb-c-new-review-request__show-repositories">
           <span class="fa fa-chevron-left"></span>
           <%- repositoriesLabel %>
          </a>
          <div class="rb-c-new-review-request__repo-detail">
           <div class="rb-c-new-review-request__main">
            <div class="rb-c-new-review-request__hint"><%- hint %></div>
           </div>
          </div>
         </div>
        </div>
    `),

    events: {
        'click .rb-c-new-review-request__show-repositories':
            '_onShowRepositoriesClicked',
    },

    /**
     * Render the page.
     */
    renderPage() {
        /* Build the main UI for the page. */
        this.$pageContent.html(this.template({
            hint: gettext('Select a repository'),
            repositoriesLabel: gettext('Repositories'),
        }));

        this._$newReviewRequestContainer = this.$pageContent.find(
            '.rb-c-new-review-request');
        this._$repoPane = this.$pageContent.find(
            '.rb-c-new-review-request__repo-pane');
        this._$repoDetailContainer = this._$repoPane.find(
            '.rb-c-new-review-request__repo-detail');
        this._$repoSelectorContainer = this._$newReviewRequestContainer.find(
            '.rb-c-sidebar');
        this._$content = this._$repoDetailContainer.find(
            '.rb-c-new-review-request__main');
        this._$hint = this._$repoDetailContainer.find(
            '.rb-c-new-review-request__hint');

        /*
         * Add the repository selector. This will live either in the page's
         * sidebar (in desktop mode) or in the page's container (in mobile
         * mode).
         */
        this._repositorySelectionView = new RB.RepositorySelectionView({
            collection: this.model.get('repositories'),
        });
        this._repositorySelectionView.render();

        this.listenTo(this._repositorySelectionView,
                      'selected',
                      repository => this.model.set('repository', repository));
        this.listenTo(this.model, 'change:repository',
                      this._onRepositoryChanged);

        if (this._preCommitView) {
            this._$hint.hide();
            this._$content.append(this._preCommitView.render().el);
        }
        if (this._postCommitView) {
            this._$hint.hide();
            this._$content.append(this._postCommitView.render().el);
        }

        /*
         * If the only two options are the "None - File attachments only"
         * pseudo-repository and one real one, pre-select the real one to speed
         * up the 80% case. Otherwise, we'll leave it at the "Select a
         * repository" screen.
         */
        const repositories = this.model.get('repositories').models;

        if (repositories.length === 2) {
            repositories[1].trigger('selected', repositories[1]);
        }

        return this;
    },

    /**
     * Handle mobile mode changes.
     *
     * This will update the parent of the repository selector. In desktop
     * mode, it will be placed in the sidebar. In mobile mode, it will be
     * placed in a container in this view, with its display managed by CSS.
     *
     * Args:
     *     inMobileMode (bool):
     *         Whether the UI is now in mobile mode.
     */
    onMobileModeChanged(inMobileMode) {
        this._repositorySelectionView.$el
            .detach()
            .appendTo(inMobileMode
                      ? this._$repoSelectorContainer
                      : this.$mainSidebar);
    },

    /**
     * Callback for when the current repository has changed.
     *
     * If the "Files Only" entry is selected, this shows the special
     * FilesOnlyPreCommitView in the right-hand pane.
     *
     * If a repository that supports fetching committed revisions is selected,
     * this will show both the pre-commit and post-commit UIs stacked
     * vertically. If the repository only supports pre-commit, only the
     * pre-commit UI is shown.
     */
    _onRepositoryChanged() {
        const repository = this.model.get('repository');

        if (repository === null) {
            /*
             * A repository is no longer selected. The user either chose
             * the File Attachments Only entry or hit the "< Repositories"
             * link on mobile.
             *
             * If on mobile, we're going to add a small delay (slightly longer
             * than the animation time) before removing any views, so that
             * they don't disappear during animation.
             */
            this._$newReviewRequestContainer
                .removeClass('js-repository-selected');

            if (this.inMobileMode) {
                _.delay(this._removeCommitViews.bind(this), 400);
            } else {
                this._removeCommitViews();
            }
        } else {
            /*
             * The user has selected a repository. Begin placing new views
             * based on the repository's capabilities.
             */
            this._$newReviewRequestContainer
                .addClass('js-repository-selected');

            this._removeCommitViews();

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
                        }),
                        $scrollContainer: this._$content,
                    });
                }
            }

            this._$hint.hide();
            this._$content.append(this._preCommitView.render().el);

            if (this._postCommitView) {
                this._$content.append(this._postCommitView.render().el);
            }
        }
    },

    /**
     * Remove the pre- and post-commit views.
     *
     * This will remove the views from the DOM and null them out, allowing
     * them to be rebuilt.
     */
    _removeCommitViews() {
        if (this._preCommitView) {
            this._preCommitView.remove();
            this._preCommitView = null;
        }

        if (this._postCommitView) {
            this._postCommitView.remove();
            this._postCommitView = null;
        }
    },

    /**
     * Handler for when the mobile-only Show Repositories link is clicked.
     *
     * Sets the page to slide back to the sidebar listing repositories.
     */
    _onShowRepositoriesClicked() {
        this._repositorySelectionView.unselect();
    },
});


})();
