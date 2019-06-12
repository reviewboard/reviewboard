/**
 * Models a generic datagrid.
 *
 * This will keep track of any selected objects, allowing subclasses to easily
 * perform operations on them.
 */
RB.DatagridPage = RB.Page.extend({
    defaults: _.defaults({
        count: 0,
        localSiteName: null,
    }, RB.Page.prototype.defaults),

    /* The type of object each row represents, for use in batch selection. */
    rowObjectType: null,

    /**
     * Initialize the model.
     */
    initialize() {
        this.selection = new Backbone.Collection([], {
            model: this.rowObjectType,
        });

        this.listenTo(this.selection, 'add remove reset',
                      () => this.set('count', this.selection.length));
    },

    /**
     * Add a selected row to be used for any actions.
     *
     * Args:
     *     id (string):
     *         The ID of the selected row.
     */
    select(id) {
        const localSiteName = this.get('localSiteName');

        this.selection.add({
            id: id,
            localSitePrefix: localSiteName ? `s/${localSiteName}/` : null,
        });
    },

    /**
     * Remove a selected row.
     *
     * Args:
     *     id (string):
     *         The ID of the row to remove.
     */
    unselect(id) {
        this.selection.remove(this.selection.get(id));
    },

    /**
     * Clear the list of selected rows.
     */
    clearSelection() {
        this.selection.reset();
    },
});
