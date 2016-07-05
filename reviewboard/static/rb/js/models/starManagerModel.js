/**
 * A model for managing the state of a RB.StarManagerView.
 *
 * Model Attributes:
 *     objects (object):
 *         A mapping of object IDs to their respective objects.
 *
 *     starred (object):
 *         The set of all starred objects. If this has a key some object ID,
 *         then the object corresponding to the object ID is starred. Otherwise
 *         it is unstarred.
 */
RB.StarManager = Backbone.Model.extend({
    defaults: function() {
        return {
            objects: {},
            starred: {}
        };
    }
});
