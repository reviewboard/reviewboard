(function() {


/**
 * A drawer containing actions that can be performed on selected objects.
 *
 * This displays any actions provided by the Django
 * :py:class:`~django.contrib.admin.ModelAdmin` class that can apply to
 * selected rows in the change list.
 */
const ActionsDrawerView = RB.DrawerView.extend({
    template: _.template(dedent`
        <p class="rb-c-drawer__summary"></p>
        <div class="rb-c-drawer__actions">
         <ul class="rb-c-drawer__action-group">
          <% _.each(actions, function(actionInfo) { %>
           <li class="rb-c-drawer__action"
               data-action-id="<%- actionInfo.id %>">
            <strong><%- actionInfo.label %></strong>
           </li>
          <% }) %>
         </ul>
        </div>
    `),

    events: {
        'click .rb-c-drawer__action': '_onActionClicked',
    },

    /**
     * Initialize the drawer.
     *
     * Args:
     *     options (object):
     *         Options for the drawer.
     *
     * Option Args:
     *     actions (Array of object):
     *         The actions to show in the drawer. Each is an object with the
     *         following keys:
     *
     *         ``id`` (:js:class:`string`):
     *             The action's identifier.
     *
     *         ``label`` (:js:class:`string`):
     *             The human-readable label.
     */
    initialize(options) {
        this.actions = options.actions;
    },

    /**
     * Render the drawer.
     *
     * Returns:
     *     ActionsDrawerView:
     *     This instance, for chaining.
     */
    render() {
        RB.DrawerView.prototype.render.call(this);

        this.$content.html(this.template({
            actions: this.actions,
        }));

        this.$summary = this.$('.rb-c-drawer__summary');

        return this;
    },

    /**
     * Handle a click on one of the action items.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _onActionClicked(e) {
        e.stopPropagation();
        e.preventDefault();

        this.trigger('actionClicked', $(e.currentTarget).data('action-id'));
    },
});


/**
 * The view for the Administration UI's Change List page.
 *
 * This manages the dynamic state of the Change List page, which is used for
 * showing all entries for a model.
 *
 * This includes a drawer for the actions that can be performed on selected
 * entries (defined in :py:class:`~django.contrib.admin.ModelAdmin`), and
 * managing the selection state in general.
 */
RB.Admin.ChangeListPageView = RB.Admin.PageView.extend({
    events: {
        'change #action-toggle': '_onToggleAllCheckboxesChanged',
        'change .action-select': '_onRowSelected',
    },

    /**
     * Initialize the page view.
     */
    initialize() {
        RB.Admin.PageView.prototype.initialize.apply(this, arguments);

        this.drawerShown = false;
    },

    /**
     * Render the page contents.
     *
     * This should be implemented by subclasses that need to render any
     * UI elements.
     */
    renderPage() {
        RB.Admin.PageView.prototype.renderPage.call(this);

        const model = this.model;

        this._$changelist = this.$pageContent.children(
            '.rb-c-admin-change-list');
        this._$form = this._$changelist.children(
            '.rb-c-admin-change-list__form');
        this._$datagrid = this._$form.children(
            '.rb-c-admin-change-list__results');
        this._datagrid = this._$datagrid.data('datagrid');
        this._$actions = this._$form.find(
            'select[name="action"]');

        const drawer = new ActionsDrawerView({
            actions: model.get('actions'),
        });
        this.setDrawer(drawer);
        this.listenTo(drawer, 'actionClicked', action => {
            this._$actions.children(`option[value="${action}"]`)
                .prop('selected', true);
            this._$form.submit();
        });

        const modelNameLower = model.get('modelName').toLowerCase();
        const modelNameLowerPlural =
            model.get('modelNamePlural').toLowerCase();

        this.listenTo(model, 'change:selectionCount', (model, count) => {
            this.drawer.$summary.text(
                N_(`${count} ${modelNameLower} selected`,
                   `${count} ${modelNameLowerPlural} selected`,
                   count));

            const showDrawer = (count > 0);

            if (showDrawer !== this._drawerShown) {
                if (showDrawer) {
                    this.drawer.show();
                } else {
                    this.drawer.hide();
                }

                this._drawerShown = showDrawer;
            }
        });
    },

    /**
     * Handle a page resize.
     *
     * This will lay out the elements to take the full height of the
     * page.
     */
    onResize() {
        this.resizeElementForFullHeight(this._$changelist);
        this.resizeElementForFullHeight(this._$form);
        this._datagrid.resizeToFit();
        this._positionDrawer();
    },

    /**
     * Position the drawer to align with the change list form.
     *
     * The drawer overlays the sidebar, but should line up vertically with
     * the change list's form (the datagrid area) rather than using a fixed
     * offset from the top. This keeps the drawer aligned as the height of
     * the content above the form changes, such as when a search result
     * summary is shown.
     *
     * This only applies in desktop mode. In mobile mode the drawer docks
     * along the bottom of the page, so any inline positioning is cleared.
     *
     * Version Added:
     *     9.0
     */
    _positionDrawer() {
        const drawer = this.drawer;

        if (drawer === null || drawer.$content === null) {
            return;
        }

        const $content = drawer.$content;

        if (this.inMobileMode) {
            $content.css({
                bottom: '',
                height: '',
                top: '',
            });

            return;
        }

        const $form = this._$form;

        /* Inset the drawer by 2em from the top and bottom of the form. */
        const margin = 2 * parseFloat($content.css('font-size'));

        $content.css({
            bottom: 'auto',
            height: $form.outerHeight() - (2 * margin),
            top: ($form.offset().top - drawer.$el.offset().top) + margin,
        });
    },

    /**
     * Handle a toggle on the checkbox in the datagrid header.
     *
     * This will toggle all rows' checkboxes to match the state of the
     * one in the header.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    _onToggleAllCheckboxesChanged(e) {
        const $toggleCheckbox = $(e.target);

        this._$datagrid.find('.action-select')
            .prop('checked', $toggleCheckbox.prop('checked'))
            .change();
    },

    /**
     * Handle a toggle on a checkbox in a row.
     *
     * This will mark the row as selected or unselected, depending on the
     * state of the checkbox.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    _onRowSelected(e) {
        const $checkbox = $(e.target);
        const objectID = $checkbox.val();

        if ($checkbox.prop('checked')) {
            this.model.select(objectID);
        } else {
            this.model.unselect(objectID);
        }
    },
});


})();
