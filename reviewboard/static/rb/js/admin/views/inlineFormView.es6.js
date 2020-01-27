/**
 * A view managing inline forms, for related objects for models.
 *
 * This allows for providing form data for a database object that relates to
 * some primary object, or deleting the object. It's managed by
 * :js:class:`RB.Admin.InlineFormGroupView`.
 */
RB.Admin.InlineFormView = Backbone.View.extend({
    events: {
        'click .rb-c-admin-form-inline__delete-action': '_onDeleteClicked',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this._$removeButton = null;
        this._$title = null;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.Admin.InlineFormView:
     *     This view, for chaining.
     */
    render() {
        this._$removeButton = this.$('.rb-c-admin-form-inline__delete-action');
        this._$title = this.$('.rb-c-admin-form-inline__title-index');

        this.listenTo(this.model, 'change:index', this._onIndexChanged);

        return this;
    },

    /**
     * Handle a change to the inline's index in the group.
     *
     * This will update the ID and title for this view, and the IDs, names,
     * and references across all elements in the form.
     */
    _onIndexChanged() {
        const index = this.model.get('index');
        const prefix = this.model.get('prefix');
        const idRegex = new RegExp(`(${prefix}-(\\d+|__prefix__))`);
        const newPrefix = `${prefix}-${index}`;

        function _updateElements(el) {
            if (el.id) {
                el.id = el.id.replace(idRegex, newPrefix);
            }

            if (el.name) {
                el.name = el.name.replace(idRegex, newPrefix);
            }

            if (el.htmlFor) {
                el.htmlFor = el.htmlFor.replace(idRegex, newPrefix);
            }

            for (let node = el.firstChild;
                 node !== null;
                 node = node.nextSibling) {
                _updateElements(node);
            }
        }

        this.el.id = newPrefix;
        this._$title.text(`#${index + 1}`);

        _updateElements(this.el);
    },

    /**
     * Handle a click event on the Delete button for the inline.
     *
     * This will trigger the ``deleteClicked`` event, allowing the parent
     * :js:class:`RB.Admin.InlineFormGroupView` to handle it.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _onDeleteClicked(e) {
        if (this.model.get('isInitial')) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        if (confirm(gettext('Are you sure you want to delete this? This cannot be undone.'))) {
            this.model.destroy();
        }
    },
});
