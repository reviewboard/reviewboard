/*
 * Models a generic datagrid.
 *
 * This will keep track of any selected objects, allowing subclasses to easily
 * perform operations on them.
 */
RB.DatagridPage = Backbone.Model.extend({
    defaults: {
        count: 0,
        localSiteName: null
    },

    /* The type of object each row represents, for use in batch selection. */
    rowObjectType: null,

    /*
     * Initializes the model.
     */
    initialize: function() {
        this.selection = new Backbone.Collection([], {
            model: this.rowObjectType
        });

        this.listenTo(this.selection, 'add remove reset', function() {
            this.set('count', this.selection.length);
        });
    },

    /*
     * Adds a selected row to be used for any actions.
     */
    select: function(id) {
        var localSiteName = this.get('localSiteName');

        this.selection.add({
            id: id,
            localSitePrefix: localSiteName ? 's/' + localSiteName + '/' : null
        });
    },

    /*
     * Removes a selected row.
     */
    unselect: function(id) {
        this.selection.remove(this.selection.get(id));
    },

    /*
     * Clears the list of selected rows.
     */
    clearSelection: function() {
        this.selection.reset();
    }
});
