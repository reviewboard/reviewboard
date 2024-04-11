/**
 * A view for managing OAuth2 tokens.
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


/**
 * Attributes for tho OAuthTokenItem model.
 *
 * Version Added:
 *     8.0
 */
interface OAuthTokenItemAttrs extends ListItemAttrs {
    /** The URL to the OAuth token list resource. */
    apiURL: string;

    /** The application name. */
    application: string;
}


/**
 * A model representing an OAuth token.
 */
@spina
class OAuthTokenItem extends ConfigFormsListItem<OAuthTokenItemAttrs> {
    static defaults: Result<Partial<OAuthTokenItemAttrs>> = {
        apiURL: '',
        application: '',
        showRemove: true,
    };
}


/**
 * A view representing a single OAuthTokenItem.
 */
@spina
class OAuthTokenItemView extends ConfigFormsListItemView<OAuthTokenItem> {
    static template = _.template(dedent`
        <span class="config-token-name"><%- application %></span>
    `);

    static actionHandlers: EventsHash = {
        'delete': '_onDeleteClicked',
    };

    /**
     * Delete the OAuth2 token.
     */
    async _onDeleteClicked() {
        try {
            await fetch(this.model.get('apiURL'), {
                method: 'DELETE',
            });

            this.model.trigger('destroy');
        } catch (err) {
            console.error('Error occurred while deleting OAuth token', err);
        }
    }
}


/**
 * Options for the OAuthTokenView.
 *
 * Version Added:
 *     8.0
 */
interface OAuthTokenViewOptions {
    /** The serialized token data. */
    tokens: OAuthTokenItemAttrs[];
}


/**
 * A view for managing OAuth2 tokens.
 */
@spina
export class OAuthTokensView extends BaseView<
    undefined,
    HTMLDivElement,
    OAuthTokenViewOptions
> {
    static template = _.template(dedent`
        <div class="oauth-token-list">
         <div class="djblets-l-config-forms-container -is-top-flush">
          <div class="oauth-token-list-empty"><%- emptyText %></div>
         </div>
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The collection of tokens. */
    collection: Collection<OAuthTokenItem>;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (OAuthTokenViewOptions):
     *         The view options.
     */
    initialize(options: OAuthTokenViewOptions) {
        this.collection = new Collection<OAuthTokenItem>(options.tokens, {
            model: OAuthTokenItem,
            parse: true,
        });
    }

    /**
     * Render the view.
     */
    protected onRender() {
        this.$el.html(OAuthTokensView.template({
            emptyText: _`You do not have any OAuth2 tokens.`,
        }));

        const listView = new ConfigFormsListView({
            ItemView: OAuthTokenItemView,
            model: new ConfigFormsList({}, {
                collection: this.collection,
            }),
        });

        listView
            .render().$el
            .prependTo(this.$('.oauth-token-list'));

        /*
         * TODO: It would be nice to update this when the last item in the list
         * gets removed, but the collection doesn't seem to be triggering
         * events correctly. This is low priority given how rarely OAuth tokens
         * are created/removed, but something to think about when we rewrite
         * ConfigForms.
         */
        this.$el.find('.oauth-token-list-empty')
            .toggle(this.collection.length === 0);
    }
}
