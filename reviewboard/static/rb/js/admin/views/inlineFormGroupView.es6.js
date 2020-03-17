/**
 * A view for managing a group of inline forms for related model objects.
 *
 * This takes care of managing the form data and rendering of multiple inline
 * forms, allowing the addition of new inline forms (up to the configured
 * limit for the model), ensuring there's a minimum available, and tracking
 * what needs to be sent to the server when saving the model.
 *
 * There's an expectation that the last form provided in the group is going to
 * be a template used for any new forms that are added.
 */
RB.Admin.InlineFormGroupView = Backbone.View.extend({
    events: {
        'click .rb-c-admin-form-inline-group__add-action': '_onAddClicked',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this._$addButton = null;
        this._$inlineTemplate = null;
        this._$inlines = null;
        this._inlineViews = [];
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.Admin.InlineFormGroupView:
     *     This object, for chaining.
     */
    render() {
        const model = this.model;
        const prefix = model.get('prefix');

        const $inlines = this.$el.children(
            '.rb-c-admin-form-inline-group__inlines');
        console.assert($inlines.length === 1);

        const $actions = this.$el.children(
            '.rb-c-admin-form-inline-group__actions');
        console.assert($actions.length === 1);

        const $addButton = $actions.children(
            '.rb-c-admin-form-inline-group__add-action');
        console.assert($addButton.length === 1);

        this._$inlines = $inlines;

        /*
         * Set up and store the template for later use. We'll remove it from
         * the DOM so we don't end up binding anything to it.
         */
        this._$inlineTemplate = $inlines.children('.-is-template')
            .detach()
            .removeClass('-is-template');
        console.assert(this._$inlineTemplate.length === 1);

        /*
         * Populate the state in the model.
         *
         * The form field names come from Django's own ManagementForm
         * (django.forms.formsets), and are outside our control. They may need
         * to be updated if Django reworks their naming or logic, though this
         * is probably unlikely.
         */
        const $initialForms = $inlines.children(`#id_${prefix}-INITIAL_FORMS`);
        const $maxNumForms = $inlines.children(`#id_${prefix}-MAX_NUM_FORMS`);
        const $minNumForms = $inlines.children(`#id_${prefix}-MIN_NUM_FORMS`);
        const $totalForms = $inlines.children(`#id_${prefix}-TOTAL_FORMS`);

        console.assert($initialForms.length === 1);
        console.assert($maxNumForms.length === 1);
        console.assert($minNumForms.length === 1);
        console.assert($totalForms.length === 1);

        const maxInlines = $maxNumForms.val();

        model.set({
            initialInlines: parseInt($initialForms.val(), 10),
            maxInlines: maxInlines === '' ? null : parseInt(maxInlines, 10),
            minInlines: parseInt($minNumForms.val(), 10),
        });

        /*
         * Update the total forms state and the visibility of the Add button
         * whenever we change the number of inlines in the group. This will also
         * update just below when we first populate the value on the model.
         */
        this.listenTo(model.inlines, 'update', () => {
            $addButton.setVisible(model.canAddInline());
            $totalForms.val(model.inlines.length);
        });

        this.listenTo(model.inlines, 'remove', this._onInlineRemoved);

        /*
         * Create and track views for every inline.
         */
        $inlines.children('.rb-c-admin-form-inline').each((index, el) => {
            this._setupInlineForm(el, {
                index: index,
                isInitial: true,
            });
        });

        console.assert(
            parseInt($totalForms.val(), 10) === model.inlines.length);

        return this;
    },

    /**
     * Add a new inline form.
     *
     * This will add a new inline form and register it, scheduling it to be
     * sent to the server when the main form is submitted.
     *
     * Returns:
     *     RB.Admin.InlineFormView:
     *     The new inline form view.
     */
    addInlineForm() {
        const newIndex = this.model.inlines.length;

        const $inline = this._$inlineTemplate.clone();
        const view = this._setupInlineForm($inline[0]);
        view.model.set('index', newIndex);

        this._$inlines.append($inline);

        this.trigger('inlineFormAdded', view);

        return view;
    },

    /**
     * Set up an inline form.
     *
     * This will construct a :js:class:`RB.Admin.InlineFormView` for the
     * element, show it, and update any form state.
     *
     * Args:
     *     el (Element):
     *         The element representing the inline form.
     *
     *     attrs (object):
     *         Attributes for the model.
     *
     * Returns:
     *     RB.Admin.InlineFormView:
     *     The new view for the element.
     */
    _setupInlineForm(el, attrs) {
        const model = this.model;

        const inline = new RB.Admin.InlineForm(_.extend({
            prefix: model.get('prefix'),
        }, attrs));

        const inlineView = new RB.Admin.InlineFormView({
            el: el,
            model: inline,
        });
        inlineView.render();

        this._inlineViews.push(inlineView);
        model.inlines.add(inline);

        return inlineView;
    },

    /**
     * Handle the removal of an inline form.
     *
     * This will remove the inline form and its view from the page, and update
     * the indexes of all other inline forms.
     *
     * Args:
     *     inline (RB.Admin.InlineForm):
     *         The inline form that was removed.
     */
    _onInlineRemoved(inline) {
        const index = inline.get('index');
        const inlineView = this._inlineViews[index];

        this._inlineViews.splice(index, 1);
        inlineView.remove();

        /* Update the indexes of all remaining form views. */
        this._inlineViews.forEach((view, i) => view.model.set('index', i));

        this.trigger('inlineFormRemoved', inlineView);
    },

    /**
     * Handle an click on Add <inline name>.
     *
     * This will add a new inline form view.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _onAddClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.addInlineForm();
    },
});
