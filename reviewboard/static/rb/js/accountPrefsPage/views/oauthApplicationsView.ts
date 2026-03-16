/**
 * A view for managing the user's OAuth2 applications.
 */

import {
    type EventsHash,
    type Result,
    BaseView,
    Collection,
    spina,
} from '@beanbag/spina';
import {
    ConfigFormsList,
    ConfigFormsListItem,
    ConfigFormsListItemView,
    ConfigFormsListView,
} from 'djblets/configForms';
import { type ListItemAttrs } from 'djblets/configForms/models/listItemModel';

import { API } from 'reviewboard/common';


/**
 * Attributes for the OAuthAppItem model
 *
 * Version Added
 *     8.0
 */
interface OAuthAppItemAttrs extends ListItemAttrs {
    /** The URL to the application list resource. */
    apiURL: string;

    /** The URL to edit this application. */
    editURL: string;

    /** Whether or not the application is enabled. */
    enabled: boolean;

    /**
     * Whether the application has been disabled for security reasons.
     *
     * This happens when the application is re-assigned to the current user
     * after the original user is removed from the Local Site that the app is
     * associated with.
     */
    isDisabledForSecurity: boolean;

    /** The name of the Local Site that the application is restricted to. */
    localSiteName: string;

    /** The name of the application. */
    name: string;

    /**
     * The username of the user who originally owned this application.
     *
     * This will only be set if the original user was removed from the Local
     * Site.
     */
    originalUser: string;
}


/**
 * Options for parsing an OAuthItem.
 *
 * Version Added:
 *     8.0
 */
interface OAuthAppItemOptions {
    /** The base for the URL for the edit view. */
    baseEditURL: string;

    /** The base for API urls. */
    baseURL: string;
}


/**
 * A model representing an OAuth application.
 */
@spina
class OAuthAppItem extends ConfigFormsListItem<OAuthAppItemAttrs> {
    static defaults: Result<Partial<OAuthAppItemAttrs>> = {
        apiURL: '',
        editURL: '',
        enabled: true,
        isDisabledForSecurity: false,
        localSiteName: '',
        name: '',
        originalUser: null,
        showRemove: true,
    };

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
     *         The values in this object will be used to generate the
     *         ``apiUrl`` and ``editURL`` properties.
     *
     * Returns:
     *     OAuthAPpItemAttrs:
     *     An object containing the properties of an OAuthAppItem.
     */
    parse(
        rsp: Partial<OAuthAppItemAttrs>,
        options: OAuthAppItemOptions,
    ): Partial<OAuthAppItemAttrs> {
        const { baseEditURL, baseURL } = options;
        const { localSiteName } = rsp;

        return _.defaults(rsp, {
            apiURL: (localSiteName
                     ? `/s/${localSiteName}${baseURL}${rsp.id}/`
                     : `${baseURL}${rsp.id}/`),
            editURL: `${baseEditURL}/${rsp.id}/`,
        });
    }
}


/**
 * A view corresponding to a single OAuth2 application.
 */
@spina
class OAuthAppItemView extends ConfigFormsListItemView<OAuthAppItem> {
    static template = _.template(dedent`
        <div class="app-entry-wrapper">
         <span class="config-app-name<% if (!enabled) {%> disabled<% } %>">
          <% if (isDisabledForSecurity) { %>
            <span class="rb-icon rb-icon-warning"
                  title="<%- disabledForSecurityText %>"></span>
          <% } %>
          <a href="<%- editURL %>"><%- name %></a>
         </span>
         <% if (isDisabledForSecurity) { %>
           <p class="disabled-warning"><%- disabledWarning %></p>
          <% } %>
         </div>
    `);

    static actionHandlers: EventsHash = {
        'delete': '_onDeleteClicked',
    };

    /**
     * Return additional rendering context.
     *
     * Returns:
     *     object:
     *     Additional rendering context.
     */
    getRenderContext(): Record<string, unknown> {
        const originalUser = this.model.get('originalUser');

        return {
            disabledForSecurityText: _`Disabled for security.`,
            disabledWarning: _`
                This application has been disabled because the user
                "${originalUser}" has been removed from the Local Site.
            `,
        };
    }

    /**
     * Delete the OAuth2 application.
     */
    _onDeleteClicked() {
        API.request({
            method: 'DELETE',
            success: () => this.model.trigger('destroy'),
            url: this.model.get('apiURL'),
        });
    }
}


/**
 * Options for the OAuthApplicationsView.
 *
 * Version Added:
 *     8.0
 */
interface OAuthApplicationsViewOptions {
    /** The serialized application information. */
    apps: Record<string, OAuthAppItemAttrs[]>;

    /** The URL of the OAuth applications list resource. */
    baseURL: string;

    /** The URL of the "edit-oauth-app" view. */
    editURL: string;
}


/**
 * A view for managing the user's OAuth2 applications.
 */
@spina
export class OAuthApplicationsView extends BaseView<
    undefined,
    HTMLDivElement,
    OAuthApplicationsViewOptions
> {
    static template = _.template(dedent`
        <div class="app-lists"></div>
        <div class="oauth-form-buttons djblets-l-config-forms-container">
         <a class="btn oauth-add-app" href="<%- editURL %>">
          <%- addApplicationText %>
         </a>
        </div>
    `);

    static listTemplate = _.template(dedent`
        <div>
         <% if (localSiteName) { %>
          <div class="djblets-l-config-forms-container">
           <h2><%- localSiteName %></h2>
          </div>
         <% } %>
         <div class="app-list">
          <div class="djblets-l-config-forms-container">
           <div class="app-list-empty-text"><%- emptyText %></div>
          </div>
         </div>
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The collections of models, organized by local site. */
    collections: Map<string | null, Collection<OAuthAppItem>>;

    /** The URL to add a new application. */
    #editURL: string;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (OAuthApplicationsViewOptions):
     *         View options.
     */
    initialize(options: OAuthApplicationsViewOptions) {
        this.collections = new Map<string | null, Collection<OAuthAppItem>>(
            Object.entries(options.apps)
                .map(([localSiteName, apps]) => ([
                    localSiteName || null,
                    new Collection<OAuthAppItem>(apps, {
                        baseEditURL: options.editURL,
                        baseURL: options.baseURL,
                        model: OAuthAppItem,
                        parse: true,
                    }),
                ]))
        );

        this.#editURL = options.editURL;
    }

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
    #renderAppList(
        localSiteName: string,
        collection: Collection<OAuthAppItem>,
    ): JQuery {
        let emptyText: string;

        if (localSiteName) {
            emptyText = _`
                You have not registered any OAuth2 applications on
                ${localSiteName}.
            `;
        } else {
            emptyText = _`You have not registered any OAuth2 applications.`;
        }

        const $entry = $(OAuthApplicationsView.listTemplate({
            emptyText: emptyText,
            localSiteName,
        }));

        const listView = new ConfigFormsListView({
            ItemView: OAuthAppItemView,
            model: new ConfigFormsList({}, { collection }),
        });

        listView
            .render().$el
            .prependTo($entry.find('.app-list'));

        /*
         * TODO: It would be nice to update this when the last item in the list
         * gets removed, but the collection doesn't seem to be triggering
         * events correctly. This is low priority given how rarely OAuth apps
         * are created/removed, but something to think about when we rewrite
         * ConfigForms.
         */
        $entry.find('.app-list-empty-text')
            .toggle(collection.length === 0);

        return $entry;
    }

    /**
     * Render the view.
     */
    protected onRender() {
        this.$el.html(OAuthApplicationsView.template({
            addApplicationText: _`Add application`,
            editURL: this.#editURL,
        }));

        const $lists = this.$('.app-lists');

        this.collections.forEach((collection, localSiteName) => {
            const $entry = this.#renderAppList(localSiteName, collection);

            if (localSiteName) {
                $lists.append($entry);
            } else {
                $lists.prepend($entry);
            }
        });
    }
}
