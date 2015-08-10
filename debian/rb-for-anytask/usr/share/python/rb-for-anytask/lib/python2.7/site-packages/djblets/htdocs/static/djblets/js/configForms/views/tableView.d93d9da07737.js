/*
 * A table-based view for a list of items.
 *
 * This is an extension to ListView that's designed for lists with multiple
 * columns of data.
 */
Djblets.Config.TableView = Djblets.Config.ListView.extend({
    tagName: 'table',
    defaultItemView: Djblets.Config.TableItemView,

    /*
     * Renders the view.
     *
     * If the element does not already have a <tbody>, one will be added.
     * All items will go under this.
     */
    render: function() {
        var $body = this.getBody();

        if ($body.length === 0) {
            this.$el.append('<tbody/>');
        }

        return Djblets.Config.ListView.prototype.render.call(this);
    },

    /*
     * Returns the body element where items will be added.
     */
    getBody: function() {
        return this.$('tbody');
    }
});
