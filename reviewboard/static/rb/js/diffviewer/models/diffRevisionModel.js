/*
 * A model representing the viewed revision of a diff.
 */
RB.DiffRevision = Backbone.Model.extend({
    defaults: {
        revision: null,
        interdiffRevision: null,
        latestRevision: null,
        isInterdiff: false,
        isDraftDiff: false
    }
});
