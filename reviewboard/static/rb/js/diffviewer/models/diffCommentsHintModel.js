/*
 * A model for giving the user hints about comments in other revisions.
 */
RB.DiffCommentsHint = Backbone.Model.extend({
    defaults: {
        hasOtherComments: false,
        diffsetsWithComments: [],
        interdiffsWithComments: []
    },

    parse: function(rsp) {
        return {
            hasOtherComments: rsp.has_other_comments,
            diffsetsWithComments: _.map(
                rsp.diffsets_with_comments,
                function(diffset) {
                    return {
                        revision: diffset.revision,
                        isCurrent: diffset.is_current
                    };
                }),
            interdiffsWithComments: _.map(
                rsp.interdiffs_with_comments,
                function(interdiff) {
                    return {
                        oldRevision: interdiff.old_revision,
                        newRevision: interdiff.new_revision,
                        isCurrent: interdiff.is_current
                    };
                })
        };
    }
});
