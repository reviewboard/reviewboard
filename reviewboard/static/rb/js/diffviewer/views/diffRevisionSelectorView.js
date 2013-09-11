/*
 * A view that allows users to select a revision of the diff to view.
 */
RB.DiffRevisionSelectorView = Backbone.View.extend({
    template: _.template([
        '<table class="revision-selector">',
        ' <tr>',
        '  <th><label for="jump_to_revision"><%- jumpToRevisionText %></label></th>',
        '  <td>',
        '   <div id="jump_to_revision" class="revisions"></div>',
        '  </td>',
        ' </tr>',
        ' <tr>',
        '  <th><label for="show_interdiff" id="interdiff_label"></label></th>',
        '  <td>',
        '   <div id="show_interdiff" class="revisions"></div>',
        '  </td>',
        ' </tr>',
        '</table>'
    ].join('')),

    events: {
        'click .jump-to-revision': '_onRevisionSelected',
        'click .jump-to-interdiff': '_onInterdiffSelected'
    },

    /*
     * Render the view.
     */
    render: function() {
        var revision = this.model.get('revision'),
            interdiffRevision = this.model.get('interdiffRevision'),
            i,
            $target;

        this.$el.html(this.template({
            jumpToRevisionText: gettext('Jump to revision:')
        }));

        this._$revisionsContainer = this.$('#jump_to_revision');
        this._$interdiffContainer = this.$('#show_interdiff');
        this._$interdiffLabel = this.$('#interdiff_label');

        for (i = 1; i <= this.options.numDiffs; i++) {
            current = (revision === i && interdiffRevision === null);

            $target = $('<span/>')
                .text(i)
                .addClass('revision jump-to-revision')
                .data('revision', i)
                .appendTo(this._$revisionsContainer);

            if (revision === i && interdiffRevision === null) {
                $target.addClass('current');
            }

            $target = $('<span/>')
                .text(i)
                .addClass('revision jump-to-interdiff')
                .data({
                    'first-revision': i < revision ? i : revision,
                    'second-revision': i < revision ? revision : i
                })
                .appendTo(this._$interdiffContainer);

            if (revision === i || interdiffRevision === i) {
                $target.addClass('current');
            }
        }

        this._$interdiffLabel.text(interpolate(
            gettext('Changes between r%s and:'),
            [revision]));

        this.listenTo(this.model, 'change', this.render);

        return this;
    },

    /*
     * Callback for when a single revision is selected.
     */
    _onRevisionSelected: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected', 0, $target.data('revision'));
    },

    /*
     * Callback for when an interdiff is selected.
     */
    _onInterdiffSelected: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected',
                     $target.data('first-revision'),
                     $target.data('second-revision'));
    }
});
