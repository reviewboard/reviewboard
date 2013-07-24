/*
 * A view for a collection of branches.
 *
 * This is presented as a <select> in the document.
 *
 * Users can listen to the "selected" event to know which branch is currently
 * chosen. This event will be triggered with the branch model as its argument.
 */
RB.BranchesView = RB.CollectionView.extend({
    tagName: 'select',

    itemViewType: RB.BranchView,

    events: {
        'change': '_onChange'
    },

    /*
     * Render the view.
     */
    render: function() {
        _.super(this).render.apply(this, arguments);

        this.collection.each(function(branch) {
            if (branch.get('isDefault')) {
                this.trigger('selected', branch);
            }
        }, this);

        return this;
    },

    /*
     * Override for CollectionView._add.
     *
     * If the newly-added branch is the default (for example, 'trunk' in SVN or
     * 'master' in git), start with it selected.
     */
    _add: function(branch) {
        _.super(this)._add.apply(this, arguments);

        if (this._rendered && branch.get('isDefault')) {
            this.trigger('selected', branch);
        }
    },

    /*
     * Callback for the 'change' event on the select node.
     *
     * Triggers 'selected' with the given model.
     */
    _onChange: function() {
        var selectedIx = this.$el.prop('selectedIndex');
        this.trigger('selected', this.collection.models[selectedIx]);
    }
});
