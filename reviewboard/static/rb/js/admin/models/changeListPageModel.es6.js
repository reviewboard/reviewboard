/**
 * The model for the Administration UI's Change List page.
 *
 * This manages the selection state for the rows in the page.
 *
 * Attributes:
 *     selection (Backbone.Collection of Backbone.Model):
 *         The collection managing selected items. Each is a basic model with
 *         an ID corresponding to the item's ID.
 *
 * Model Attributes:
 *     actions (Array of object):
 *         The actions that are enabled for items on the page. Each is an
 *         object with the following keys:
 *
 *         ``id`` (:js:class:`string`):
 *             The action's identifier.
 *
 *         ``label`` (:js:class:`string`):
 *             The human-readable label.
 */
RB.Admin.ChangeListPage = RB.Page.extend({
    defaults: _.defaults(RB.Page.prototype.defaults, {
        actions: [],
        selectionCount: 0,
    }),

    /**
     * Initialize the page model.
     */
    initialize() {
        RB.Page.prototype.initialize.apply(this, arguments);

        this.selection = new Backbone.Collection();
        this.listenTo(this.selection, 'add remove reset',
                      () => this.set('selectionCount', this.selection.length));
    },

    /**
     * Mark an item as selected.
     *
     * Args:
     *     id (number):
     *         The ID of the item to mark as selected.
     */
    select(id) {
        this.selection.add({
            id: id,
        });
    },

    /**
     * Mark an item as no longer being selected.
     *
     * Args:
     *     id (number):
     *         The ID of the item to unselect.
     */
    unselect(id) {
        this.selection.remove(this.selection.get(id));
    },
});
