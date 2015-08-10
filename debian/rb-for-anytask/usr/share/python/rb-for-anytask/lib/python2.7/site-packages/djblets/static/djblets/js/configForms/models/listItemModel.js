/*
 * Base class for an item in a list for config forms.
 *
 * ListItems provide text representing the item, optionally linked. They
 * can also provide zero or more actions that can be invoked on the item
 * by the user.
 *
 * Actions can have 'id', 'type', 'label', 'enabled', 'propName', 'iconName',
 * 'danger', and 'children' attributes.
 *
 * 'id' is a unique ID for the action. It is used when registering action
 * handlers, and will also be appended to the class name for the action.
 *
 * 'type' is optional, but if set to 'checkbox', a checkbox will be presented.
 *
 * 'propName' is used only for checkbox actions. It specifies the attribute
 * on the model that will be set to reflect the checkbox.
 *
 * 'iconName' specifies the name of the icon to display next to the action.
 * This is the "iconname" part of "rb-icon-iconname".
 *
 * 'danger' indicates that the action will cause some permanent,
 * undoable change. This is used only for buttons.
 *
 * 'children' indicates the action is a menu action that has sub-actions.
 *
 * As a convenience, if showRemove is true, this will provide a default
 * action for removing the item.
 */
Djblets.Config.ListItem = Backbone.Model.extend({
    defaults: {
        text: null,
        editURL: null,
        showRemove: false,
        canRemove: true,
        loading: false,
        removeLabel: gettext('Remove')
    },

    /*
     * Initializes the item.
     *
     * If showRemove is true, this will populate a default Remove action
     * for removing the item.
     */
    initialize: function(options) {
        options = options || {};

        this.actions = options.actions || [];

        if (this.get('showRemove')) {
            this.actions.push({
                id: 'delete',
                label: this.get('removeLabel'),
                danger: true,
                enabled: this.get('canRemove')
            });
        }
    }
});
