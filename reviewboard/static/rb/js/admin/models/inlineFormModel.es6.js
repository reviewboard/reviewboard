/**
 * The model for an inline form.
 *
 * This tracks some of the state of the inline, including its index within
 * a group and the prefix for any IDs.
 *
 * Model Attributes:
 *     index (number):
 *         The index within the group.
 *
 *     isInitial (boolean):
 *         Whether this is an initial inline group (one that existed on page
 *         load, based on an entry in the database).
 *
 *     prefix (string):
 *         The prefix for any IDs and form field names.
 */
RB.Admin.InlineForm = Backbone.Model.extend({
    defaults: {
        index: null,
        isInitial: false,
        prefix: null,
    },
});
