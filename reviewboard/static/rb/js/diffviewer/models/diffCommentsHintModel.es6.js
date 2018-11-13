/**
 * A model for giving the user hints about comments in other revisions.
 *
 * Model Attributes:
 *     diffsetsWithComments (Array of object):
 *         An array of diffset revisions to show the comment hint for.
 *
 *     hasOtherComments (boolean):
 *         Whether there are any comments on other revisions.
 *
 *     interdiffsWithComments (Array of object):
 *         An array of interdiff revisions to show the comment hint for.
 */
RB.DiffCommentsHint = Backbone.Model.extend({
    /**
     * Return the defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The defaults for the model.
     */
    defaults() {
        return {
            diffsetsWithComments: [],
            hasOtherComments: false,
            interdiffsWithComments: [],
        };
    },

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The data received from the server.
     *
     * Returns:
     *     object:
     *     The parsed result.
     */
    parse(rsp) {
        return {
            hasOtherComments: rsp.has_other_comments,
            diffsetsWithComments: rsp.diffsets_with_comments.map(
                diffset => ({
                    revision: diffset.revision,
                    isCurrent: diffset.is_current,
                })),
            interdiffsWithComments: rsp.interdiffs_with_comments.map(
                interdiff => ({
                    oldRevision: interdiff.old_revision,
                    newRevision: interdiff.new_revision,
                    isCurrent: interdiff.is_current,
                })),
        };
    },
});
