/**
 * A view for managing state on a form.
 *
 * This provides some standard behavior for setting up form widgets and
 * handling collapsable fieldsets, along with managing subforms.
 */
RB.FormView = Backbone.View.extend({
    events: {
        'click .rb-c-form-fieldset__toggle': '_onToggleFieldSetClicked',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this._$subforms = null;
        this._subformsByGroup = {};
        this._formWidgetsInitialized = false;
    },

    /**
     * Render the view.
     *
     * This will set up any subforms that might be available within the form.
     *
     * Returns:
     *     RB.FormView:
     *     This object, for chaining.
     */
    render() {
        this._$subforms = this.$('.rb-c-form-fieldset.-is-subform');

        if (this._$subforms.length > 0) {
            this._setupSubforms();
        }

        this.setupFormWidgets();

        return this;
    },

    /**
     * Set up state for widgets on the form.
     *
     * This will ensure that widgets are set up correctly on the form, or on
     * a part of the form. This will take care to re-initialize widgets if
     * they've already been initialized before (useful when dynamically adding
     * new sections of a form).
     *
     * This supports only a few known types of widgets (Django date/time
     * widgets and related object selectors).
     *
     * Args:
     *     $el (jQuery, optional):
     *         A starting point for finding the widgets. If not provided, all
     *         widgets in the form will be set up.
     */
    setupFormWidgets($el) {
        if ($el === undefined) {
            $el = this.$el;
        }

        /*
         * Update some state for Django widgets. We've quite possibly made use
         * of widgets in the form that need to be initialized, and Django
         * doesn't have much fine-grained support for doing this, so we need
         * to take a heavy-handed approach.
         *
         * Django (up through 3.0 at least) performs similar logic.
         */
        if (window.DateTimeShortcuts &&
            $el.find('.datetimeshortcuts').length > 0) {
            if (this._formWidgetsInitialized) {
                /*
                 * Yep, we have to remove *all* of these... DateTimeShortcuts
                 * has no granular widget support.
                 */
                $('.datetimeshortcuts').remove();
            }

            DateTimeShortcuts.init();
        }

        if (window.SelectFilter) {
            $el.find('.selectfilter').each((i, el) => {
                const parts = el.name.split('-');
                SelectFilter.init(el.id, parts[parts.length - 1], false);
            });

            $el.find('.selectfilterstacked').each((i, el) => {
                const parts = el.name.split('-');
                SelectFilter.init(el.id, parts[parts.length - 1], true);
            });
        }

        this._formWidgetsInitialized = true;
    },

    /**
     * Set the visibility of one or more subforms.
     *
     * This will toggle visibility of a single subform, hide all subforms,
     * or hide all subforms except one.
     *
     * Args:
     *     options (object):
     *         Options to control visibility.
     *
     * Option Args:
     *     group (string):
     *         The registered group for the subforms.
     *
     *     hideOthers (boolean):
     *         Whether to hide any subforms other than the one specified by
     *         ``subformID``.
     *
     *     subformID (string):
     *         A single subform to set the visibility state for. If not
     *         provided, this will toggle visibility of all subforms in the
     *         group.
     *
     *     visible (boolean):
     *         Whether to make the selected subform visible. This is only used
     *         if ``hideOthers`` is not provided.
     */
    setSubformVisibility(options) {
        console.assert(_.isObject(options),
                       'An options object must be provided.');

        const group = options.group;
        const subformID = options.subformID;
        const visible = options.visible;

        console.assert(group, 'Missing option "group"');

        const subformIDs = this._subformsByGroup[group];
        console.assert(subformIDs, `Invalid subform group ${group}`);

        if (options.hideOthers || !subformID) {
            _.each(subformIDs, ($subform, id) => {
                const isHidden = (subformID === undefined
                                  ? !visible
                                  : (id !== subformID));

                $subform.prop({
                    disabled: isHidden,
                    hidden: isHidden,
                });
            });
        } else {
            console.assert(visible !== undefined, 'Missing option "visible"');

            const $subform = subformIDs[subformID];
            console.assert($subform, `Invalid subform ID ${subformID}`);

            $subform.prop({
                disabled: !visible,
                hidden: !visible,
            });
        }
    },

    /**
     * Set up state and event handlers for subforms.
     *
     * This will begin tracking all the subforms on the page, and connect
     * subform visibility to any associated controllers.
     */
    _setupSubforms() {
        const configuredControllers = {};

        this._$subforms.each((i, subformEl) => {
            const $subform = $(subformEl);
            const controllerID = $subform.data('subform-controller');
            const subformID = $subform.data('subform-id');
            let group = $subform.data('subform-group');
            let $controller;

            if (!subformID) {
                console.error('Subform %o is missing data-subform-id=',
                              subformEl);
                return;
            }

            if (!group && !controllerID) {
                console.error(
                    'Subform %o is missing either data-subform-group= ' +
                    'or data-subform-controller=',
                    subformEl);
                return;
            }

            /*
             * If we have a controller ID provided, look it up and ensure
             * we're using the right group.
             */
            if (controllerID) {
                $controller = this.$(`#${controllerID}`);

                console.assert($controller.length === 1,
                               `Missing controller #${controllerID}`);

                const controllerGroup =
                    $controller.data('subform-group');

                /*
                 * If the subform specifies an explicit group, and it
                 * specified a controller, make sure they match up. While
                 * we could work around an issue here, we'd rather make the
                 * developer fix their code.
                 */
                if (group === undefined) {
                    group = controllerGroup;
                } else if (controllerGroup !== group) {
                    console.error('Subform %o and controller %s have ' +
                                  'different values for data-subform-group',
                                  subformEl, controllerID);
                    return;
                }
            }

            /* Register the subforms so that they can be looked up later. */
            if (!this._subformsByGroup.hasOwnProperty(group)) {
                this._subformsByGroup[group] = {};
            }

            this._subformsByGroup[group][subformID] = $subform;

            /*
             * If we have a controller associated, set the current subform's
             * visibility based on that value, and listen for changes.
             */
            if ($controller) {
                this.setSubformVisibility({
                    group: group,
                    subformID: subformID,
                    visible: $controller.val() === subformID,
                });

                if (!configuredControllers[controllerID]) {
                    configuredControllers[controllerID] = true;

                    $controller.on('change', () => this.setSubformVisibility({
                        group: group,
                        subformID: $controller.val(),
                        visible: true,
                        hideOthers: true,
                    }));
                }
            }
        });
    },

    /**
     * Handle the showing or collapsing of a fieldset.
     *
     * This will set the appropriate state on the fieldset to show or hide
     * the content.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event on the Show/Hide button.
     */
    _onToggleFieldSetClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        const $toggle = $(e.target);
        const $fieldset = $toggle.closest('.rb-c-form-fieldset');

        if ($fieldset.hasClass('-is-collapsed')) {
            $fieldset.removeClass('-is-collapsed');
            $toggle.text(gettext('(Hide)'));
        } else {
            $fieldset.addClass('-is-collapsed');
            $toggle.text(gettext('(Show)'));
        }
    },
});
