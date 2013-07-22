describe('newReviewRequest/views/PostCommitView', function() {
    var repository,
        commits,
        model,
        view;

    beforeEach(function() {
        repository = new RB.Repository({
            name: 'Repo',
            supportsPostCommit: true
        });

        spyOn(repository.branches, 'sync').andCallFake(
            function(method, collection, options) {
                options.success({
                    stat: 'ok',
                    branches: [
                        {
                            name: 'master',
                            commit: '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                            'default': true
                        },
                        {
                            name: 'release-1.7.x',
                            commit: '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                            'default': false
                        },
                        {
                            name: 'release-1.6.x',
                            commit: 'a15d0e635064a2e1929ce1bf3bc8d4aa65738b64',
                            'default': false
                        }
                    ]
                });
            }
        );

        spyOn(repository, 'getCommits').andCallFake(function(start) {
            commits = new RB.RepositoryCommits([], {
                urlBase: _.result(this, 'url') + 'commits/',
                start: start
            });

            spyOn(commits, 'sync').andCallFake(
                function(method, collection, options) {
                    options.success({
                        stat: 'ok',
                        commits: [
                            {
                                authorName: 'Author 1',
                                date: '2013-07-22T03:51:50Z',
                                id: '3',
                                message: 'Summary 1\n\nMessage 1'
                            },
                            {
                                authorName: 'Author 2',
                                date: '2013-07-22T03:50:46Z',
                                id: '2',
                                message: 'Summary 2\n\nMessage 2'
                            },
                            {
                                authorName: 'Author 3',
                                date: '2013-07-21T08:05:45Z',
                                id: '1',
                                message: 'Summary 3\n\nMessage 3'
                            }
                        ]
                    });
                }
            );

            return commits;
        });

        model = new RB.PostCommitModel({ repository: repository });
        view = new RB.PostCommitView({ model: model });

        spyOn(RB.PostCommitView.prototype, '_onCreateReviewRequest').andCallThrough();

        expect(repository.branches.sync).toHaveBeenCalled();
    });

    it('Render', function() {
        view.render();

        expect(commits.sync).toHaveBeenCalled();

        expect(view._branchesView.$el.children().length).toBe(3);
        expect(view._commitsView.$el.children().length).toBe(3);
    });

    it('Create', function() {
        var commit,
            call;

        view.render();

        spyOn(RB.ReviewRequest.prototype, 'save').andReturn();

        commit = commits.models[1];
        commit.trigger('create', commit);

        expect(RB.PostCommitView.prototype._onCreateReviewRequest).toHaveBeenCalled();
        expect(RB.ReviewRequest.prototype.save).toHaveBeenCalled();

        expect(RB.ReviewRequest.prototype.save.calls.length).toBe(1);

        call = RB.ReviewRequest.prototype.save.mostRecentCall;
        expect(call.object.get('commitID')).toBe(commit.get('id'));
    });
});
