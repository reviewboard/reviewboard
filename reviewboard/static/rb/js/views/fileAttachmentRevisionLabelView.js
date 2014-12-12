/*
 * A view which explains the currently-shown revision of the file attachment.
 */
RB.FileAttachmentRevisionLabelView = Backbone.View.extend({
    events: {
        'click .select-latest': '_onSelectLatest',
        'click .select-changed': '_onSelectChanged'
    },

    /*
     * Templates for various strings. We use _.template instead of interpolate
     * to make sure that revision strings are HTML-escaped.
     */
    template: _.template([
        '<h1><%- header %></h1>',
        '<% if (detail) { %><p><%= detail %><% } %>'
    ].join('')),
    _interdiffTemplate: _.template(gettext(
        'Changes between revision <%- revision %> and <%- interdiffRevision %>')),
    _latestTemplate: _.template(gettext(
        'Diff Revision <%- revision %> (Latest)')),
    _oldHeaderTemplate: _.template(gettext('Diff Revision <%- revision %>')),
    _oldDetailTemplate: _.template(
        /* Translators: This string should be valid HTML (including any necessary escaping for entities). */
        gettext('This is not the most recent revision of the diff.' +
            ' The <a href="#" class="select-latest">latest diff</a> is revision' +
            ' <%- latestRevision %>. <a href="#" class="select-changed">' +
            'See what\'s changed.</a>')),

     /*
     * Initialize the view.
     */
    initialize: function() {
        this.listenTo(this.model, 'change', this.render);
    },

    /*
     * Render the view.
     */
    render: function() {
        var revision = this.model.get('fileRevision'),
            interdiffRevision = this.model.get('diffRevision'),
            latestRevision = this.model.get('numRevisions'),
            header = '',
            detail = null;

        if (interdiffRevision) {
            header = this._interdiffTemplate({
                revision: revision,
                interdiffRevision: interdiffRevision
            });
        } else if (revision === latestRevision) {
            header = this._latestTemplate({
                revision: revision
            });
        } else {
            header = this._oldHeaderTemplate({
                revision: revision
            });
            detail = this._oldDetailTemplate({
                revision: revision,
                latestRevision: latestRevision
            });
        }

        this.$el.html(this.template({
            header: header,
            detail: detail
        }));

        return this;
    },

    /*
     * Callback when the "latest diff" link is clicked in the "This is not the
     * most recent revision" explanation.
     */
    _onSelectLatest: function(ev) {
        ev.preventDefault();
        this.trigger('revisionSelected', [0, this.model.get('numRevisions')]);
        return false;
    },

    /*
     * Callback for when "See what's changed" is clicked in the "This is not
     * the most recent revision" explanation.
     */
    _onSelectChanged: function(ev) {
        ev.preventDefault();
        this.trigger('revisionSelected',
                     [this.model.get('fileRevision'),
                      this.model.get('numRevisions')]);
        return false;
    }
});