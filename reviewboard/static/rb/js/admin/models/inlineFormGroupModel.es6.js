/**
 * The model managing a group of inline form.
 *
 * This tracks a list of inline forms referenced used in the group, and
 * provides state to send back to the server when saving the group and
 * related utility functions.
 *
 * Attributes:
 *     inlines (Backbone.Collection of RB.Admin.InlineForm):
 *         The inline forms that are part of this group.
 *
 * Model Attributes:
 *     initialInlines (number):
 *         The number of inlines originally provided to the page.
 *
 *     maxInlines (number):
 *         The maximum number of inlines allowed on the page.
 *
 *     minInlines (number):
 *         The minimum number of inlines allowed on the page.
 *
 *     prefix (string):
 *         The prefix for any IDs and form field names in the group.
 */
RB.Admin.InlineFormGroup = Backbone.Model.extend({
    defaults: {
        initialInlines: 0,
        maxInlines: 0,
        minInlines: 0,
        prefix: null,
    },

    /**
     * Initialize the group.
     */
    initialize() {
        this.inlines = new Backbone.Collection([], {
            model: RB.Admin.InlineForm,
        });
    },

    /**
     * Return whether a new inline can be added.
     *
     * A new inline can be added if there's no maximum, or the maximum has
     * not yet been reached.
     *
     * Returns:
     *     boolean:
     *     ``True`` if a new inline can be added. ``False`` if the limit has
     *     been reached.
     */
    canAddInline() {
        const maxInlines = this.get('maxInlines');

        return maxInlines === null || this.inlines.length < maxInlines;
    },
});
