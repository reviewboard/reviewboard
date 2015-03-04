/*
 * The DiffCommitIndexView displays a table containing diff commit entries.
 *
 * The view contains all the commits associated with the diff revision selected
 * by the diff revision selector.
 */
RB.DiffCommitIndexView = Backbone.View.extend({
    /*
     * Initialize the view.
     */
    initialize: function() {
        this._$itemsTable = null;

        this.collection = this.options.collection;
        this.listenTo(this.collection, 'update', this.update);
    },

    _itemTemplate: _.template([
        '<tr>',
        ' <td class="diff-file-icon"></td>',
        ' <td><%- summary %></td>',
        ' <td><%- authorName %></td>',
        '</tr>'
    ].join('')),

    _tableHeader: _.template([
        '<thead>',
        ' <tr>',
        '  <th></th>',
        '  <th><%- gettext("Summary") %></th>',
        '  <th><%- gettext("Author") %></th>',
        ' </tr>',
        '</thead>'
    ].join(''))(),

    /*
     * Render the diff commit list table.
     */
    render: function() {
        this._$itemsTable = $('<table/>').appendTo(this.$el);

        this.update();

        return this;
    },

    /*
     * Update the diff commit list table.
     *
     * This will populate the table with entries from the associated
     * DiffCommitCollection. If the collection is empty (i.e., the selected
     * diff revision has no commits associated with it), then the diff commit
     * list table will be hidden.
     */
    update: function() {
        var $tbody;

        this._$itemsTable.empty();

        if (this.collection.length > 0) {
            $tbody = $('<tbody/>');

            this.collection.each(function(diffCommit) {
                $tbody.append(this._itemTemplate(diffCommit.attributes));
            }, this);

            this._$itemsTable.append(this._tableHeader);
            this._$itemsTable.append($tbody);

            this.$el.show();
        } else {
            this.$el.hide();
        }
    }
});
