(function() {


const addApplicationText = gettext('Add application');
const disabledForSecurityText = gettext('Disabled for security.');
const disabledWarningTemplate = gettext('This application has been disabled because the user "%s" has been removed from the Local Site.');
const emptyText = gettext('You have not registered any OAuth2 applications.');
const localSiteEmptyText = gettext('You have not registered any OAuth2 applications on %s.');


/**
 * A model representing an OAuth application.
 *
 * Model Attributes:
 *     apiURL (string):
 *         The URL to the application list reosurce.
 *
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
 *     localSiteName (string):
 *         The name of the LocalSite the application is restricted to.

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
        apiURL: '',
        editURL: '',
        enabled: true,
        isDisabledForSecurity: false,
        localSiteName: '',
        name: '',
        originalUser: null,
        showRemove: true,
    }, Djblets.Config.ListItem.prototype.defaults),

    /**
     * Parse a raw object into the properties of an OAuthAppItem.
     *
     * Args:
     *     rsp (object):
     *         The raw properties of the item.
     *
     *     options (object):
     *         Options for generating properties.
     *
     *         The values in this object will be used to generate the ``apiUrl``
     *         and ``editURL`` properties.
     *
     * Option Args:
     *     baseURL (string):
     *         The base API URL for the object.
     *
     *     baseEditURL (string):
     *         The base URL for the edit view.
     *
     * Returns:
     *     object:
     *     An object containing the properties of an OAuthAppItem.
     */
    parse(rsp, options) {
        const {baseEditURL, baseURL} = options;
        const {localSiteName} = rsp;

        return _.defaults(rsp, {
            apiURL: (localSiteName
                     ? `/s/${localSiteName}${baseURL}${rsp.id}/`
                     : `${baseURL}${rsp.id}/`),
            editURL: `${baseEditURL}/${rsp.id}/`,
        });
    },
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
        <div class="app-lists"></div>
        <div class="oauth-form-buttons djblets-l-config-forms-container">
         <a class="btn oauth-add-app" href="<%- editURL %>">
          ${addApplicationText}
         </a>
        </div>
    `),

    listTemplate: _.template(dedent`
        <div>
         <% if (localSiteName) { %>
          <div class="djblets-l-config-forms-container">
           <h2><%- localSiteName %></h2>
          </div>
         <% } %>
         <div class="app-list">
          <div class="djblets-l-config-forms-container">
           <%- emptyText %>
          </div>
         </div>
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
        this.collections = new Map(
            Object.entries(options.apps)
                .map(([localSiteName, apps]) => ([
                    localSiteName || null,
                    new Backbone.Collection(apps, {
                        model: OAuthAppItem,
                        parse: true,
                        baseEditURL: options.editURL,
                        baseURL: options.baseURL,
                     }),
                ]))
        );

        this._editURL = options.editURL;

        window.view = this;
    },

    /**
     * Render an application list for the given LocalSite.
     *
     * Args:
     *     localSiteName (string):
     *         The name of the LocalSite or ``null``.
     *
     *     collection (Backbone.Collection):
     *         The collection of models.
     *
     * Returns:
     *     jQuery:
     *     The rendered list.
     */
    _renderAppList(localSiteName, collection) {
        const $entry = $(this.listTemplate({
            emptyText: (localSiteName
                        ? interpolate(localSiteEmptyText, [localSiteName])
                        : emptyText),
            localSiteName,
        }));

        const listView = new Djblets.Config.ListView({
            ItemView: OAuthAppItemView,
            model: new Djblets.Config.List({}, {collection}),
        });

        listView
            .render().$el
            .prependTo($entry.find('.app-list'));

        return $entry;
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
            editURL: this._editURL,
        }));

        const $lists = this.$('.app-lists');

        this.collections.forEach((collection, localSiteName) => {
            const $entry = this._renderAppList(localSiteName, collection);

            if (localSiteName) {
                $lists.append($entry);
            } else {
                $lists.prepend($entry);
            }
        });

        return this;
    },
});


})();
