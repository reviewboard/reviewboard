/**
 * A view which explains the currently-shown revision of the file attachment.
 */
RB.FileAttachmentRevisionLabelView = Backbone.View.extend({
    events: {
        'click .select-latest': '_onSelectLatest',
        'click .select-changed': '_onSelectChanged',
    },

    /*
     * Templates for various strings. We use _.template instead of interpolate
     * to make sure that revision strings are HTML-escaped.
     */
    template: _.template(dedent`
        <p><%- header %></p>
        <% if (detail) { %><p><%= detail %></p><% } %>
    `),
    _interdiffTemplate: _.template(gettext('This file attachment has multiple revisions. Showing changes between revision <%- diffAgainstRevision %> and <%- revision %>.')),
    _latestTemplate: _.template(gettext('This file attachment has multiple revisions. Showing revision <%- revision %> (latest).')),
    _oldHeaderTemplate: _.template(gettext('This file attachment has multiple revisions. Showing revision <%- revision %>.')),
    _oldDetailTemplate: _.template(
        /* Translators: This string should be valid HTML (including any necessary escaping for entities). */
        gettext('This is not the most recent revision of the file. The <a href="#" class="select-latest">latest version</a> is revision <%- latestRevision %>. <a href="#" class="select-changed">See what\'s changed.</a>')),

    /**
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model, 'change', this.render);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.FileAttachmentRevisionLabelView:
     *     This object, for chaining.
     */
    render() {
        const revision = this.model.get('fileRevision');
        const diffAgainstRevision = this.model.get('diffRevision');
        const latestRevision = this.model.get('numRevisions');

        let header = '';
        let detail = null;

        if (diffAgainstRevision) {
            header = this._interdiffTemplate({
                revision: revision,
                diffAgainstRevision: diffAgainstRevision,
            });
        } else if (revision === latestRevision) {
            header = this._latestTemplate({
                revision: revision,
            });
        } else {
            header = this._oldHeaderTemplate({
                revision: revision,
            });
            detail = this._oldDetailTemplate({
                revision: revision,
                latestRevision: latestRevision,
            });
        }

        this.$el.html(this.template({
            header: header,
            detail: detail,
        }));

        return this;
    },

    /**
     * Callback when the "latest diff" link is clicked.
     *
     * This link is in the "This is not the most recent revision" explanation.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the action.
     */
    _onSelectLatest(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this.trigger('revisionSelected', [0, this.model.get('numRevisions')]);
    },

    /**
     * Callback for when "See what's changed" is clicked.
     *
     * This link is in the "This is not the most recent revision" explanation.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the action.
     */
    _onSelectChanged(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this.trigger('revisionSelected',
                     [this.model.get('fileRevision'),
                      this.model.get('numRevisions')]);
    },
});
