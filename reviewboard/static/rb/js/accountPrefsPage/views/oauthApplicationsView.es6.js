{


const addApplicationText = gettext('Add application');
const disabledForSecurityText = gettext('Disabled for security.');
const disabledWarningTemplate = gettext('This application has been disabled because the user "%s" has been removed from the Local Site.');
const emptyText = gettext('You have not registered any OAuth2 applications.');


/**
 * A model representing an OAuth application.
 *
 * Attributes:
 *     enabled (boolean):
 *         Whether or not the application is enabled.
 *
 *     editURL (string):
 *         The URL to edit this application.
 *
 *     isDisabledForSecurity (bool):
 *         When true, this attribute indicates that the application was
 *         re-assigned to the current user because the original user was
 *         removed from the Local Site associated with this.
 *
 *     name (string):
 *         The name of the application.
 *
 *     originalUser (string):
 *         The username of the user who originally owned this application. This
 *         will only be set if :js:attr:`enabled` is ``false``.
 *
 *     showRemove (boolean):
 *         Whether or not the "Remove Item" link should be shown.
 *
 *         This is always true.
 */
const OAuthAppItem = Djblets.Config.ListItem.extend({
    defaults: _.defaults({
        editURL: '',
        enabled: true,
        isDisabledForSecurity: false,
        name: '',
        originalUser: null,
        showRemove: true,
    }, Djblets.Config.ListItem.prototype.defaults),

});


/**
 * A view corresponding to a single OAuth2 application.
 */
const OAuthAppItemView = Djblets.Config.ListItemView.extend({
    template: _.template(dedent`
        <div class="app-entry-wrapper">
         <span class="config-app-name<% if (!enabled) {%> disabled<% } %>">
          <% if (isDisabledForSecurity) { %>
            <span class="rb-icon rb-icon-warning"
                  title="${disabledForSecurityText}"></span>
          <% } %>
          <a href="<%- editURL %>"><%- name %></a>
         </span>
         <% if (isDisabledForSecurity) { %>
           <p class="disabled-warning"><%- disabledWarning %></p>
          <% } %>
         </div>
    `),

    actionHandlers: {
        'delete': '_onDeleteClicked',
    },

    /**
     * Return additional rendering context.
     *
     * Returns:
     *     object:
     *     Additional rendering context.
     */
    getRenderContext() {
        return {
            disabledWarning: interpolate(disabledWarningTemplate,
                                         [this.model.get('originalUser')])
        };
    },

    /**
     * Delete the OAuth2 application.
     */
    _onDeleteClicked() {
        RB.apiCall({
            url: this.model.get('apiURL'),
            method: 'DELETE',
            success: () => this.model.trigger('destroy'),
            error: (xhr) => alert(xhr.errorText),
        });
    },
});


/**
 * A view for managing the user's OAuth2 applications.
 */
RB.OAuthApplicationsView = Backbone.View.extend({
    template: _.template(dedent`
        <div class="app-list">
         <div class="config-forms-list-empty box-recessed">
          ${emptyText}
         </div>
        </div>
        <div class="oauth-form-buttons">
         <a class="btn oauth-add-app" href="<%- editURL %>">
          ${addApplicationText}
         </a>
        </div>
    `),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         View options.
     *
     * Option Args:
     *     apps (array):
     *         The array of serialized application information.
     *
     *     addText (string):
     *         The localized text for adding an option.
     *
     *     editURL (string):
     *         The URL of the "edit-oauth-app" view.
     *
     *     emptyText (string):
     *         The localized text for indicating there are no applications.
     */
    initialize(options) {
        this.collection = new Backbone.Collection(options.apps, {
            model: OAuthAppItem,
        });

        this._editURL = options.editURL;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.OAuthApplicationsView:
     *     This view.
     */
    render() {
        this.$el.html(this.template({
            addText: this._addText,
            editURL: this._editURL,
            emptyText: this._emptyText,
        }));

        this._$list = this.$('.app-list');
        this._listView = new Djblets.Config.ListView({
            ItemView: OAuthAppItemView,
            model: new Djblets.Config.List({}, {
                collection: this.collection,
            }),
        });

        this._listView
            .render().$el
            .addClass('box-recessed')
            .prependTo(this._$list);

        return this;
    },
});


}
