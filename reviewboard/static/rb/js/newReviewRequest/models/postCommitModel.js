/*
 * Basic data used by the PostCommitView.
 */
RB.PostCommitModel = Backbone.Model.extend({
    defaults: {
        repository: null,
        branch: null
    }
});
