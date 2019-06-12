/**
 * Basic data used by the PostCommitView.
 *
 * Model Attributes:
 *     branch (RB.RepositoryBranch):
 *         The selected branch.
 *
 *     repository (RB.Repository):
 *         The selected repository.
 */
RB.PostCommitModel = Backbone.Model.extend({
    defaults: {
        branch: null,
        repository: null,
    },
});
