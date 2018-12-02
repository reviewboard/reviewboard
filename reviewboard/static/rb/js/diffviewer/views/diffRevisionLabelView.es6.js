/**
 * A view which explains the currently-shown revision of the diff.
 */
RB.DiffRevisionLabelView = Backbone.View.extend({
    events: {
        'click .select-latest': '_onSelectLatest',
        'click .select-changed': '_onSelectChanged',
    },

    /**
     * Templates for various strings.
     *
     * We use _.template instead of interpolate to make sure that revision
     * strings are HTML-escaped.
     */
    template: _.template(dedent`
        <h1><%- header %></h1>
        <% if (detail) { %><p><%= detail %><% } %>
    `),
    _interdiffTemplate: _.template(gettext(
        'Changes between revision <%- revision %> and <%- interdiffRevision %>')),
    _latestTemplate: _.template(gettext(
        'Diff Revision <%- revision %> (Latest)')),
    _oldHeaderTemplate: _.template(gettext('Diff Revision <%- revision %>')),
    _oldDetailTemplate: _.template(
        /* Translators: This string should be valid HTML (including any necessary escaping for entities). */
        gettext('This is not the most recent revision of the diff. The <a href="#" class="select-latest">latest diff</a> is revision <%- latestRevision %>. <a href="#" class="select-changed">See what\'s changed.</a>')),

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
     *     RB.DiffRevisionLabelView:
     *     This object, for chaining.
     */
    render() {
        const revision = this.model.get('revision');
        const latestRevision = this.model.get('latestRevision');
        let header = '';
        let detail = null;

        if (this.model.get('isInterdiff')) {
            const interdiffRevision = this.model.get('interdiffRevision');

            header = this._interdiffTemplate({
                revision: revision,
                interdiffRevision: interdiffRevision,
            });
        } else if (revision === latestRevision) {
            header = this._latestTemplate({
                revision: revision,
            });
        } else if (this.model.get('isDraftDiff')) {
            header = gettext('Draft diff');
            /* Translators: This string should be valid HTML (including any necessary escaping for entities). */
            detail = gettext('This diff is part of your current draft. Other users will not see this diff until you publish your draft.');
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
     * This is shown in the "This is not the most recent revision"
     * explanation.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onSelectLatest(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger('revisionSelected',
                     [0, this.model.get('latestRevision')]);
    },

    /*
     * Callback for when "See what's changed" is clicked.
     *
     * This is shown in the "This is not the most recent revision"
     * explanation.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onSelectChanged(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger('revisionSelected',
                     [this.model.get('revision'),
                      this.model.get('latestRevision')]);
    },
});
