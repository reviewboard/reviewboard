{


const addApplicationText = gettext('Add application');
const emptyText = gettext('You have not registered any OAuth2 applications.');


/**
 * A model representing an OAuth application.
 *
 * Attributes:
 *
 *     editURL (string):
 *         The URL to edit this application.
 *
 *     name (string):
 *         The name of the application.
 *
 *     showRemove (boolean):
 *         Whether or not the "Remove Item" link should be shown.
 *
 *         This is always true.
 */
const OAuthAppItem = Djblets.Config.ListItem.extend({
    defaults: _.defaults({
        editURL: '',
        name: '',
        showRemove: true,
    }, Djblets.Config.ListItem.prototype.defaults),
});


/**
 * A view corresponding to a single OAuth2 application.
 */
const OAuthAppItemView = Djblets.Config.ListItemView.extend({
    template: _.template(dedent`
        <span class="config-app-name">
         <a href="<%- editURL %>"><%- name %></a>
        </span>
    `),

    actionHandlers: {
        'delete': '_onDeleteClicked',
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
         <div class="app-list-empty box-recessed">
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
        this._$empty = this.$('.app-list-empty');
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
