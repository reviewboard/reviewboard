suite('rb/newReviewRequest/views/PostCommitView', function() {
    let repository;
    let commits;
    let model;
    let view;

    beforeEach(function() {
        repository = new RB.Repository({
            name: 'Repo',
            supportsPostCommit: true,
        });

        spyOn(repository.branches, 'sync').and.callFake(
            (method, collection, options) => {
                options.success({
                    stat: 'ok',
                    branches: [
                        {
                            name: 'master',
                            commit: '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                            'default': true,
                        },
                        {
                            name: 'release-1.7.x',
                            commit: '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                            'default': false,
                        },
                        {
                            name: 'release-1.6.x',
                            commit: 'a15d0e635064a2e1929ce1bf3bc8d4aa65738b64',
                            'default': false,
                        },
                    ],
                });
            }
        );

        spyOn(repository, 'getCommits').and.callFake(options => {
            commits = new RB.RepositoryCommits([], {
                urlBase: _.result(this, 'url') + 'commits/',
                start: options.start,
                branch: options.branch,
            });

            spyOn(commits, 'sync').and.callFake(
                (method, collection, options) => {
                    options.success({
                        stat: 'ok',
                        commits: [
                            {
                                authorName: 'Author 1',
                                date: '2013-07-22T03:51:50Z',
                                id: '3',
                                message: 'Summary 1\n\nMessage 1',
                            },
                            {
                                authorName: 'Author 2',
                                date: '2013-07-22T03:50:46Z',
                                id: '2',
                                message: 'Summary 2\n\nMessage 2',
                            },
                            {
                                authorName: 'Author 3',
                                date: '2013-07-21T08:05:45Z',
                                id: '1',
                                message: 'Summary 3\n\nMessage 3',
                            },
                        ],
                    });
                }
            );

            return commits;
        });

        model = new RB.PostCommitModel({ repository: repository });
        view = new RB.PostCommitView({
            model: model,
            $scrollContainer: $('<div>'),
        });

        spyOn(RB.PostCommitView.prototype, '_onCreateReviewRequest')
            .and.callThrough();

        expect(repository.branches.sync).toHaveBeenCalled();
    });

    it('Render', function() {
        view.render();

        expect(commits.sync).toHaveBeenCalled();

        expect(view._branchesView.$el.children().length).toBe(3);
        expect(view._commitsView.$el.children().length).toBe(3);
    });

    it('Create', function() {
        view.render();

        spyOn(RB.ReviewRequest.prototype, 'save').and.returnValue();

        const commit = commits.models[1];
        commit.trigger('create', commit);

        expect(RB.PostCommitView.prototype._onCreateReviewRequest).toHaveBeenCalled();
        expect(RB.ReviewRequest.prototype.save).toHaveBeenCalled();

        expect(RB.ReviewRequest.prototype.save.calls.count()).toBe(1);

        const call = RB.ReviewRequest.prototype.save.calls.mostRecent();
        expect(call.object.get('commitID')).toBe(commit.get('id'));
    });

    describe('Error handling', function() {
        describe('Branches', function() {
            const xhr = { errorText: 'Oh no' };
            let returnError;

            beforeEach(function() {
                spyOn(repository.branches, 'fetch').and.callFake(
                    (options, context) => {
                        if (returnError) {
                            options.error.call(context, repository.branches,
                                               xhr);
                        } else {
                            options.success.call(context);
                        }
                    });

                returnError = true;

                spyOn(RB.PostCommitView.prototype, '_showLoadError')
                    .and.callThrough();

                view._loadBranches();
            });

            it('UI state', function() {
                expect(repository.branches.fetch).toHaveBeenCalled();
                expect(view._showLoadError).toHaveBeenCalledWith(
                    'branches', xhr);
                expect(view._branchesView.$el.css('display')).toBe('none');
                expect(view._$error).toBeTruthy();
                expect(view._$error.length).toBe(1);
                expect(view._commitsView).toBeFalsy();
                expect(view._$error.find('.error-text').text().strip())
                    .toBe('Oh no');
                expect(view._$error.find('a')[0].id).toBe('reload_branches');
            });

            it('Reloading', function() {
                spyOn(view, '_loadBranches').and.callThrough();

                /* Make sure the spy is called from the event handler. */
                view.delegateEvents();

                returnError = false;

                expect(view._$error).toBeTruthy();
                const $reload = view._$error.find('#reload_branches');
                expect($reload.length).toBe(1);
                $reload.click();

                expect(view._loadBranches).toHaveBeenCalled();

                expect(view._$error).toBe(null);
                expect(view._branchesView.$el.css('display')).not.toBe('none');
            });
        });

        describe('Commits', function() {
            const xhr = { errorText: 'Oh no' };
            let returnError;

            beforeEach(function() {
                view.render();

                spyOn(RB.RepositoryCommits.prototype, 'fetch').and.callFake(
                    (options, context) => {
                        if (returnError) {
                            options.error.call(context, repository.commits,
                                               xhr);
                        } else {
                            options.success.call(context);
                        }
                    });

                returnError = true;

                spyOn(RB.PostCommitView.prototype, '_showLoadError')
                    .and.callThrough();

                view._loadCommits();
            });

            it('UI state', function() {
                expect(view._commitsCollection.fetch).toHaveBeenCalled();
                expect(view._showLoadError).toHaveBeenCalledWith(
                    'commits', xhr);
                expect(view._commitsView.$el.css('display')).toBe('none');
                expect(view._$error).toBeTruthy();
                expect(view._$error.length).toBe(1);
                expect(view._commitsView).toBeTruthy();
                expect(view._commitsView.$el.css('display')).toBe('none');
                expect(view._$error.find('.error-text').text().strip())
                    .toBe('Oh no');
                expect(view._$error.find('a')[0].id).toBe('reload_commits');
            });

            it('Reloading', function() {
                spyOn(view, '_loadCommits').and.callThrough();

                /* Make sure the spy is called from the event handler. */
                view.delegateEvents();

                returnError = false;

                expect(view._$error).toBeTruthy();
                const $reload = view._$error.find('#reload_commits');
                expect($reload.length).toBe(1);
                $reload.click();

                expect(view._loadCommits).toHaveBeenCalled();

                expect(view._$error).toBe(null);

                /*
                 * Chrome returns an empty string, while Firefox returns
                 * "block".
                 */
                const display = view._commitsView.$el.css('display');
                expect(display === 'block' || display === '').toBe(true);
            });
        });
    });
});
