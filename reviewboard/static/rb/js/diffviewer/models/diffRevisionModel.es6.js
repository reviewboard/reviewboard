/**
 * A model representing the viewed revision of a diff.
 *
 * Model Attributes:
 *     interdiffRevision (number):
 *         The second revision of an interdiff range to view.
 *
 *     isDraftDiff (boolean):
 *         Whether or not the currently displayed diff belongs to a review
 *         request draft.
 *
 *     isInterdiff (boolean):
 *         Whether or not an interdiff is being displayed.
 *
 *     latestRevision (number):
 *         The latest revision available.
 *
 *     revision (number):
 *         The revision (or first part of an interdiff range) to view.
 */
RB.DiffRevision = Backbone.Model.extend({
    defaults: {
        interdiffRevision: null,
        isDraftDiff: false,
        isInterdiff: false,
        latestRevision: null,
        revision: null,
    },

    /**
     * Parse the attributes into model attributes.
     *
     * Args:
     *     attrs (object):
     *         The attributes to parse.
     *
     * Returns:
     *     object:
     *     The parsed attributes.
     */
    parse(attrs) {
       return {
            interdiffRevision: attrs.interdiff_revision,
            isDraftDiff: attrs.is_draft_diff,
            isInterdiff: attrs.is_interdiff,
            latestRevision: attrs.latest_revision,
            revision: attrs.revision,
        };
    },
});
