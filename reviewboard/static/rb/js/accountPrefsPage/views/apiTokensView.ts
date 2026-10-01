/**
 * Renders and manages a page of API tokens.
 */

import {
    type ButtonView,
    type ComponentChild,
    type DialogViewOpenOptions,
    type DialogViewOptions,
    type MenuButtonView,
    DialogSize,
    DialogView,
    MenuItem,
    MenuItemType,
    MenuItemsCollection,
    MenuItemsRadioGroup,
    craft,
    paint,
    showConfirmDialog,
    showErrorDialog,
} from '@beanbag/ink';
import {
    type EventsHash,
    type Result,
    BaseCollection,
    BaseView,
    spina,
} from '@beanbag/spina';
import CodeMirror from 'codemirror';
import {
    ConfigFormsList,
    ConfigFormsListItemView,
    ConfigFormsListView,
} from 'djblets/configForms';
import {
    type ListItemViewRenderContext,
} from 'djblets/configForms/views/listItemView';
import moment from 'moment';

import {
    APIToken,
    UserSession,
} from 'reviewboard/common';
import {
    type APITokenAttrs,
} from 'reviewboard/common/resources/models/apiTokenModel';
import { ConfigFormsResourceListItem } from 'reviewboard/configForms';
import {
    ResourceListItemAttrs,
} from 'reviewboard/configForms/models/resourceListItemModel';
import {
    DateTimeInlineEditorView,
    InlineEditorView,
} from 'reviewboard/ui';


const POLICY_CUSTOM = 'custom';
const POLICY_CUSTOM_LABEL = _`Custom`;


/**
 * An API token policy available for selection.
 *
 * Version Added:
 *     9.0
 */
interface APITokenPolicy {
    /** The unique ID of the token policy. */
    id: string;

    /** The display name of the token policy. */
    name: string;

    /** The token policy document. */
    policyDoc: object;
}


/**
 * Attributes for the APITokenItem model.
 *
 * Version Added:
 *     9.0
 */
interface APITokenItemAttrs extends ResourceListItemAttrs<APIToken> {
    /**
     * The type of policy.
     *
     * This is the ID of one of the server-provided policies, or
     * POLICY_CUSTOM.
     */
    policyType: string;

    /**
     * Whether the token policy is currently being saved.
     *
     * Version Added:
     *     9.0
     */
    isSavingPolicy: boolean;

    /** The date and time of last use for the token. */
    lastUsed: string | null;

    /** The name of the local site that the token is limited to. */
    localSiteName: string | null;
}


/**
 * Represents an API token in the list.
 *
 * This tracks the policy type for the token, and provides an action for
 * removing the token.
 */
@spina
class APITokenItem extends ConfigFormsResourceListItem<
    APITokenAttrs,
    APIToken,
    APITokenItemAttrs
> {
    static defaults: Result<Partial<APITokenItemAttrs>> = {
        isSavingPolicy: false,
        lastUsed: null,
        localSiteName: null,
        policyType: 'read-write',
        showRemove: true,
    };

    static syncAttrs = [
        'deprecated',
        'expired',
        'expires',
        'id',
        'invalidReason',
        'invalidDate',
        'lastUsed',
        'note',
        'policy',
        'tokenValue',
        'valid',
    ];

    /**********************
     * Instance variables *
     **********************/

    /** The collection that owns the item. */
    collection: APITokenItemCollection;

    /**
     * The last custom policy used for this token.
     *
     * This lets the user switch to a built-in policy and back again without
     * losing their custom policy while the page is still open.
     *
     * Version Added:
     *     9.0
     */
    #lastCustomPolicy: (object | null) = null;

    /**
     * Initialize the item.
     *
     * This computes the type of policy used, for display.
     */
    initialize(attributes?: Partial<APITokenItemAttrs>) {
        super.initialize(attributes);

        const policyDoc = this.get('policy') || {};
        const policyType = this._guessPolicyType(policyDoc);

        if (policyType === POLICY_CUSTOM) {
            this.#lastCustomPolicy = policyDoc;
        }

        this.set('policyType', policyType);
    }

    /**
     * Create an APIToken resource for the given attributes.
     *
     * Args:
     *     attrs (object):
     *         Additional attributes for the APIToken.
     *
     * Returns:
     *     RB.APIToken:
     *     The new APIToken instance.
     */
    createResource(
        attrs: APITokenAttrs,
    ): APIToken {
        return new APIToken(Object.assign({
            localSitePrefix: this.collection.localSitePrefix,
            userName: UserSession.instance.get('username'),
        }, attrs));
    }

    /**
     * Set the provided expiration date on the token and save it.
     *
     * Args:
     *     expires (string):
     *         The new expiration date for the token. If this is an
     *         empty string, the token will be set to have no expiration.
     */
    saveExpires(expires: string) {
        this._saveAttribute('expires', expires);
    }

    /**
     * Set the provided note on the token and save it.
     *
     * Args:
     *     note (string):
     *         The new note for the token.
     */
    saveNote(note: string) {
        this._saveAttribute('note', note);
    }

    /**
     * Set the provided policy on the token and save it.
     *
     * Version Changed:
     *     9.0:
     *     * The promise now resolves to a boolean indicating if saving was
     *       successful.
     *
     *     * Errors are now handled by this function, rather than the caller.
     *
     * Args:
     *     policy (object):
     *         The new policy for the token.
     *
     * Returns:
     *     Promise<boolean>:
     *     A promise which resolves when the operation is complete. The
     *     result of the promise will be a boolean indicating if the save
     *     completed.
     */
    async savePolicy(
        policy: object,
    ): Promise<boolean> {
        const prevPolicy = this.get('policy');

        this.set('isSavingPolicy', true);

        try {
            await this._saveAttribute('policy', policy);

            return true;
        } catch (e) {
            /* Restore the previous policy. */
            this.resource.set('policy', prevPolicy);

            const rsp = e?.xhr?.errorPayload;

            if (rsp?.err?.type === 'request-field-error') {
                const policyError = rsp?.fields?.policy;

                if (policyError) {
                    e = policyError;
                }
            }

            showErrorDialog({
                error: e,
                title: _`Error setting the token policy`,
            });

            return false;
        } finally {
            this.set('isSavingPolicy', false);
        }
    }

    /**
     * Set the token to one of the built-in policies and save it.
     *
     * If the token was using a custom policy, it will be preserved in case
     * the user switches back. This only lasts while the page is open.
     *
     * Version Added:
     *     9.0
     *
     * Args:
     *     policyType (string):
     *         The ID of the built-in policy to use.
     *
     * Returns:
     *     Promise<boolean>:
     *     A promise which resolves to whether the policy type was saved.
     */
    async setPolicyType(
        policyType: string,
    ): Promise<boolean> {
        console.assert(policyType !== POLICY_CUSTOM);

        /* Check first if the policy document has changed. */
        const policyDoc = this.collection.policiesMap[policyType].policyDoc;

        if (_.isEqual(policyDoc, this.get('policy'))) {
            /* The policy didn't change. Consider this a success. */
            this.set('policyType', policyType);

            return true;
        }

        if (this.get('policyType') === POLICY_CUSTOM) {
            /*
             * The previous policy was a custom policy. Store it locally
             * in case the user switches back.
             */
            this.#lastCustomPolicy = this.get('policy');
        }

        /* Save the policy. */
        const saved = await this.savePolicy(policyDoc);

        if (saved) {
            /* This was successful, so update to the new policy type. */
            this.set('policyType', policyType);
        }

        return saved;
    }

    /**
     * Save a custom policy for the token.
     *
     * Version Added:
     *     9.0
     *
     * Args:
     *     policy (object):
     *         The custom policy document.
     *
     * Returns:
     *     Promise<boolean>:
     *     A promise which resolves to whether the policy was saved.
     */
    async saveCustomPolicy(
        policy: object,
    ): Promise<boolean> {
        const saved = await this.savePolicy(policy);

        if (saved) {
            this.#lastCustomPolicy = policy;
            this.set('policyType', POLICY_CUSTOM);
        }

        return saved;
    }

    /**
     * Return the custom policy to show in the policy editor.
     *
     * This will be the last custom policy used for this token, or the
     * default custom policy if there isn't one.
     *
     * Version Added:
     *     9.0
     *
     * Returns:
     *     object:
     *     The custom policy document.
     */
    getCustomPolicy(): object {
        return this.#lastCustomPolicy ||
               this.get('policy') ||
               APIToken.defaultPolicies.custom;
    }

    /**
     * Set an attribute on the token and save it.
     *
     * This is a helper function that will set an attribute on the token
     * and save it, but only after the token is ready.
     *
     * Args:
     *     attr (string):
     *         The name of the attribute to set.
     *
     *     value (object or string):
     *         The new value for the attribute.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async _saveAttribute<
        TAttrType extends Backbone._StringKey<APITokenAttrs>
    >(
        attr: TAttrType,
        value: APITokenAttrs[A],
    ) {
        await this.resource.ready();
        this.resource.set(attr, value);
        await this.resource.save();
    }

    /**
     * Guess the policy type for a given policy definition.
     *
     * This compares the policy against the server-provided policies.
     * If one of them matches, its ID will be returned. Otherwise, this
     * assumes it's a custom policy.
     *
     * Args:
     *     policyDoc (object):
     *         A policy document.
     *
     * Returns:
     *     string:
     *     The policy type that was matched.
     */
    _guessPolicyType(policyDoc: unknown) {
        for (const tokenPolicy of this.collection.policies) {
            if (_.isEqual(policyDoc, tokenPolicy.policyDoc)) {
                return tokenPolicy.id;
            }
        }

        return POLICY_CUSTOM;
    }
}


/**
 * Options for the APITokenItemCollection.
 *
 * Version Added:
 *     9.0
 */
interface APITokenItemCollectionOptions {
    /** The URL prefix to use for the local site, if present. */
    localSitePrefix: string;

    /**
     * The list of token policies available for new and existing tokens.
     *
     * Version Added:
     *     9.0
     */
    policies: APITokenPolicy[];
}


/**
 * A collection of APITokenItems.
 *
 * This works like a standard Backbone.Collection, but can also have
 * a LocalSite URL prefix attached to it, for use in API calls in
 * APITokenItem.
 */
@spina
class APITokenItemCollection extends BaseCollection<
    APITokenItem,
    APITokenItemCollectionOptions
> {
    static model = APITokenItem;

    /**********************
     * Instance variables *
     **********************/

    /** The URL prefix to add for Local Site specific tokens. */
    localSitePrefix: string;

    /**
     * The list of token policies available for new and existing tokens.
     *
     * Version Added:
     *     9.0
     */
    policies: APITokenPolicy[];

    /**
     * A map of token policy IDs to instances.
     *
     * Version Added:
     *     9.0
     */
    policiesMap: Record<string, APITokenPolicy>;

    /**
     * Initialize the collection.
     *
     * Args:
     *     models (Array of object):
     *         Initial models for the collection.
     *
     *     options (object):
     *         Additional options for the collection.
     *
     * Option Args:
     *     localSitePrefix (string):
     *         The URL prefix for the current local site, if any.
     *
     *     policies (Array of APITokenPolicy):
     *         The list of token policies available for new and existing
     *         tokens.
     *
     *         Version Added:
     *             9.0
     */
    initialize(
        models: APITokenItem[],
        options: APITokenItemCollectionOptions,
    ) {
        this.localSitePrefix = options.localSitePrefix;

        const policies = options.policies;
        const policiesMap: Record<string, APITokenPolicy> = {};

        for (const policy of policies) {
            policiesMap[policy.id] = policy;
        }

        /*
         * Add the custom policy to the map, since it will be used for
         * much of the UI building. Adding it here simplifies a lot.
         */
        policiesMap[POLICY_CUSTOM] = {
            id: POLICY_CUSTOM,
            name: POLICY_CUSTOM_LABEL,
            policyDoc: APIToken.defaultPolicies.custom,
        };

        this.policies = policies;
        this.policiesMap = policiesMap;
    }
}


/**
 * Provides an editor for constructing or modifying a custom policy definition.
 *
 * This renders as a modal dialog with a CodeMirror editor inside of it. The
 * editor is set to allow easy editing of a JSON payload, complete with
 * lintian checking. Only valid policy payloads can be saved to the server.
 */
@spina
class PolicyEditorView extends DialogView<APITokenItem> {
    static id = 'custom_policy_editor';
    static title = _`Custom Token Access Policy`;

    /**********************
     * Instance variables *
     **********************/

    /** The CodeMirror instance. */
    #codeMirror: CodeMirror.Editor = null;

    /** The policy editor <textarea> element. */
    #textarea: HTMLTextAreaElement = null;

    /** The save buttons. */
    #saveButtons: ButtonView[];

    /**
     * Initialize the editor.
     *
     * Args:
     *     options (DialogViewOptions):
     *         Additional options for view construction.
     */
    initialize(options: Partial<DialogViewOptions>) {
        super.initialize(_.defaults(options, {
            size: DialogSize.LARGE,
        }));
    }

    /**
     * Open the dialog.
     *
     * Args:
     *     options (DialogViewOpenOptions, optional):
     *         Whether to show the dialog as a modal.
     */
    open(options: DialogViewOpenOptions = {}) {
        super.open(options);

        this.#codeMirror = CodeMirror.fromTextArea(this.#textarea, {
            gutters: ['CodeMirror-lint-markers'],
            lineNumbers: true,
            lineWrapping: true,
            lint: {
                onUpdateLinting: this._onUpdateLinting.bind(this),
            },
            matchBrackets: true,
            mode: {
                highlightFormatting: true,
                name: 'application/json',
            },
            styleSelectedText: true,
            theme: 'rb default',
        });
        this.#codeMirror.focus();
    }

    /**
     * Render the body of the dialog.
     *
     * Returns:
     *     ComponentChild or Array of ComponentChild:
     *     The content for the dialog body.
     */
    protected renderBody(): ComponentChild | ComponentChild[] {
        const manualURL = `${MANUAL_URL}webapi/2.0/api-token-policy/`;
        const policy = this.model.getCustomPolicy();

        this.#textarea = paint<HTMLTextAreaElement>`
            <textarea>${JSON.stringify(policy, null, '  ')}</textarea>
        `;

        const $instructions = $('<p>')
            .html(_`
                You can limit access to the API through a custom policy. See
                the <a href="${manualURL}" target="_blank">documentation</a>
                on how to write policies.
            `);

        return paint`
            <div>
             <p>${$instructions[0]}</p>
             ${this.#textarea}
            </div>
        `;
    }

    /**
     * Render the primary actions for the dialog.
     *
     * Returns:
     *     ComponentChild or Array of ComponentChild:
     *     The content for the primary actions.
     */
    protected renderPrimaryActions(): ComponentChild | ComponentChild[] {
        this.#saveButtons = [
            craft<ButtonView>`
                <Ink.DialogAction class="save-button"
                                  callback=${() => this.save(false)}>
                 ${_`Save and continue editing`}
                </Ink.DialogAction>
            `,
            craft<ButtonView>`
                <Ink.DialogAction type="primary"
                                  class="save-button"
                                  callback=${() => this.save(true)}>
                 ${_`Save`}
                </Ink.DialogAction>
            `,
        ];

        return this.#saveButtons;
    }

    /**
     * Render the secondary actions for the dialog.
     *
     * Returns:
     *     ComponentChild or Array of ComponentChild:
     *     The content for the primary actions.
     */
    protected renderSecondaryActions(): ComponentChild | ComponentChild[] {
        return paint`
            <Ink.DialogAction callback=${() => this.cancel()}>
             ${_`Cancel`}
            </Ink.DialogAction>
        `;
    }

    /**
     * Cancel the editor.
     */
    cancel() {
        this.remove();
    }

    /**
     * Save the editor.
     *
     * The policy will be saved to the server for immediate use.
     *
     * Args:
     *     closeOnSave (boolean):
     *         Whether the editor should close after saving.
     */
    async save(closeOnSave: boolean) {
        const policyStr = this.#codeMirror.getValue().trim();
        let policy;

        try {
            policy = JSON.parse(policyStr);
        } catch (e) {
            if (e instanceof SyntaxError) {
                showErrorDialog({
                    error: e,
                    title: _`Syntax error in your policy`,
                });

                return;
            } else {
                throw e;
            }
        }

        if (await this.model.saveCustomPolicy(policy)) {
            /*
             * The save was successful. Check if the user requested to close
             * the dialog.
             */
            if (closeOnSave) {
                this.remove();
            }
        }
    }

    /**
     * Handler for when lintian checking has run.
     *
     * This will disable the save buttons if there are any lintian errors.
     *
     * Args:
     *     annotationsNotSorted (Array):
     *         An array of the linter annotations.
     */
    _onUpdateLinting(annotationsNotSorted: unknown[]) {
        const disabled = (annotationsNotSorted.length > 0);

        this.#saveButtons.forEach(button => {
            button.disabled = disabled;
        });
    }
}


/**
 * Renders an APITokenItem to the page, and handles actions.
 *
 * This will display the information on the given token. Specifically,
 * the token value, the note, the expiration date and the actions.
 *
 * This also handles deleting the token when the Remove action is clicked,
 * and displaying the policy editor when choosing a custom policy.
 */
@spina
class APITokenItemView extends ConfigFormsListItemView<APITokenItem> {
    static EMPTY_NOTE_PLACEHOLDER = _`Click to describe this token`;

    static template = _.template(_`
        <div class="rb-c-config-api-tokens__main">
         <div class="rb-c-config-api-tokens__value">
          <input readonly="readonly" value="<%- tokenValue %>">
         </div>
         <span class="fa fa-clipboard js-copy-token"
               title="Copy to clipboard"></span>
        </div>
        <div class="rb-c-config-api-tokens__info">
         <% if (deprecated) { %>
          <p class="rb-c-config-api-tokens__deprecation-notice">
           This token uses a deprecated format. You should remove it and
           generate a new one.
          </p>
         <% } %>
         <% if (valid) { %>
          <% if (lastUsed) { %>
           <p class="rb-c-config-api-tokens__usage -has-last-used">
            Last used
            <time class="timesince" datetime="<%= lastUsed %>"></time>.
           </p>
          <% } else { %>
           <p class="rb-c-config-api-tokens__usage">Never used.</p>
          <% } %>
          <% if (expired) { %>
           <p class="rb-c-config-api-tokens__token-state -is-expired">
            <span>Expired <%= expiresTimeHTML %>.</span>
           </p>
          <% } else if (expires) { %>
           <p class="rb-c-config-api-tokens__token-state -has-expires">
            <span>Expires <%= expiresTimeHTML %>.</span>
           </p>
          <% } else { %>
           <p class="rb-c-config-api-tokens__token-state">
            <span>Never expires.</span>
           </p>
          <% } %>
         <% } else { %>
          <p class="rb-c-config-api-tokens__token-state -is-invalid">
           Invalidated
           <time class="timesince" datetime="<%= invalidDate %>"></time>:
           <%= invalidReason %>
          </p>
         <% } %>
        </div>
        <div class="rb-c-config-api-tokens__actions"></div>
        <div class="rb-c-config-api-tokens__note-field">
         <span class="rb-c-config-api-tokens__note"></span>
        </div>
    `);

    static events: EventsHash = {
        'click .js-copy-token': '_onCopyClicked',
    };

    static actionHandlers: EventsHash = {
        'delete': '_onRemoveClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The expiration date. */
    #$expires: JQuery = null;

    /** The API token note. */
    #$note: JQuery = null;

    /** The current state of the API token. */
    #$tokenState: JQuery = null;

    /**
     * The menu button for choosing a token policy.
     *
     * Version Added:
     *     9.0
     */
    #policyMenuButton: MenuButtonView = null;

    /**
     * A mapping of built-in policy IDs to their menu items.
     *
     * Version Added:
     *     9.0
     */
    #policyMenuItems = new Map<string, MenuItem>();

    /**
     * The radio group for the built-in policy menu items.
     *
     * Version Added:
     *     9.0
     */
    #policyRadioGroup: MenuItemsRadioGroup = null;

    /**
     * Initialize the view.
     */
    initialize() {
        const model = this.model;
        const resource = model.resource;

        this.listenTo(resource, 'change:expires', this._updateExpires);
        this.listenTo(resource, 'change:note', this._updateNote);
        this.listenTo(model, 'change:policyType', this.#updatePolicyMenu);
        this.listenTo(model, 'change:isSavingPolicy', this.#updatePolicyBusy);
    }

    /**
     * Render the view.
     */
    protected onRender() {
        super.onRender();

        this.#renderPolicyMenu();

        this.#$tokenState = this.$('.rb-c-config-api-tokens__token-state');
        this.#$expires = this.#$tokenState
            .not('.is-invalid')
            .find('span');

        this.#$note = this.$('.rb-c-config-api-tokens__note');
        const noteEditor = new InlineEditorView({
            editIconClass: 'rb-icon rb-icon-edit',
            el: this.#$note,
            hasShortButtons: true,
        });
        noteEditor.render();

        this.listenTo(noteEditor, 'beginEdit', () => {
            noteEditor.setValue(this.model.get('note'));
        });
        this.listenTo(noteEditor, 'complete',
                      value => this.model.saveNote(value));

        const expires = moment(this.model.get('expires'))
            .local()
            .format('YYYY-MM-DDTHH:mm');

        const expiresView = new DateTimeInlineEditorView({
            descriptorText: 'Expires ',
            el: this.#$expires[0],
            formatResult: value => {
                if (value) {
                    value = moment(value).local().format();
                    const today = moment().local();
                    const expired = today.isAfter(value);
                    const prefix = expired ? 'Expired' : 'Expires';

                    if (expired) {
                        this.#$tokenState.addClass('-is-expired');
                    }

                    return (dedent`
                        ${prefix}
                        <time class="timesince" datetime="${value}"></time>.
                    `);
                } else {
                    this.#$tokenState.removeClass('-is-expired');

                    return 'Never expires.';
                }
            },
            hasShortButtons: true,
            rawValue: expires,
        })
        .on({
            beginEdit: () => this.#$tokenState.removeClass('-is-expired'),
            cancel: () => {
                if (this.model.get('expired')) {
                    this.#$tokenState.addClass('-is-expired');
                }
            }
        });
        expiresView.render();

        this.listenTo(expiresView, 'complete', (value) => {
            value = value ? moment(value).local().format() : '';
            this.model.saveExpires(value);
        });

        this._updateExpires();
        this._updateNote();
    }

    /**
     * Return the parent element for item actions.
     *
     * Returns:
     *     jQuery:
     *     The element to attach the actions to.
     */
    getActionsParent(): JQuery {
        return this.$('.rb-c-config-api-tokens__actions');
    }

    /**
     * Return additional rendering context.
     *
     * Returns:
     *     ListItemViewRenderContext:
     *     Additional rendering context.
     */
    getRenderContext(): ListItemViewRenderContext {
        const expires = this.model.get('expires');

        return {
            expiresTimeHTML:
                `<time class="timesince" datetime="${expires}"></time>`,
        };
    }

    /**
     * Render the menu button for choosing a token policy.
     *
     * Each built-in policy will be shown as a radio item. A separate
     * "Custom policy..." is shown last, which will show the policy editor
     * when clicked.
     *
     * Version Added:
     *     9.0
     */
    #renderPolicyMenu() {
        const cid = this.cid;
        const policyMenuItems = this.#policyMenuItems;
        const radioGroup = new MenuItemsRadioGroup();

        policyMenuItems.clear();

        let maxLabelLen = POLICY_CUSTOM_LABEL.length;

        const policyItems = this.model.collection.policies.map(
            tokenPolicy => {
                const policyID = tokenPolicy.id;
                const policyName = tokenPolicy.name;
                const menuItem = new MenuItem({
                    id: `api-token-${cid}-policy-${policyID}`,
                    label: policyName,
                    onClick: () => this.#onPolicySelected(policyID),
                    radioGroup: radioGroup,
                    type: MenuItemType.RADIO_ITEM,
                });

                policyMenuItems.set(policyID, menuItem);

                maxLabelLen = Math.max(maxLabelLen, policyName.length);

                return menuItem;
            });

        const menuItems = new MenuItemsCollection([
            ...policyItems,
            {
                type: MenuItemType.SEPARATOR,
            },
            {
                id: `api-token-${cid}-policy-custom`,
                label: _`Custom policy...`,
                onClick: () => this.#openPolicyEditor(),
            },
        ]);

        this.#policyRadioGroup = radioGroup;
        this.#policyMenuButton = craft<MenuButtonView>`
            <Ink.MenuButton
              class="rb-c-config-api-tokens__policy-menu"
              menuAriaLabel=${_`Token access policy`}
              menuItems=${menuItems}
              />
        `;

        /*
         * Set a minimum width for the menu button so it doesn't resize when
         * the option changes. We're using ch units, which is going to give
         * a bit more width than we need, but it'll be fine.
         */
        const policyMenuButtonEl = this.#policyMenuButton.el;
        policyMenuButtonEl.style.setProperty(
            '--rb-c-config-api-tokens-policy-label-min-width',
            `${maxLabelLen}ch`,
        );

        this.$spinnerParent.prepend(policyMenuButtonEl);

        this.#updatePolicyMenu();
        this.#updatePolicyBusy();
    }

    /**
     * Update the policy menu to reflect the token's policy type.
     *
     * This sets the label on the menu button and checks the matching
     * built-in policy, if any.
     *
     * Version Added:
     *     9.0
     */
    #updatePolicyMenu() {
        const model = this.model;
        const policyType = model.get('policyType');
        const menuItem = this.#policyMenuItems.get(policyType);

        /* Set the label on the policy. */
        this.#policyMenuButton.label =
            model.collection.policiesMap[policyType].name;

        /*
         * If it's a radio button, mark it checked. Otherwise (if it's custom),
         * uncheck the previous one.
         */
        if (menuItem) {
            menuItem.set('checked', true);
        } else {
            this.#policyRadioGroup.checkedMenuItem?.set('checked', false);
        }
    }

    /**
     * Update the busy state of the policy menu button.
     *
     * Version Added:
     *     9.0
     */
    #updatePolicyBusy() {
        this.#policyMenuButton.busy = this.model.get('isSavingPolicy');
    }

    /**
     * Handle selecting a built-in policy from the menu.
     *
     * If saving fails, the menu will go back to showing the token's current
     * policy.
     *
     * Version Added:
     *     9.0
     *
     * Args:
     *     policyType (string):
     *         The ID of the selected policy.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the operation.
     */
    async #onPolicySelected(
        policyType: string,
    ): Promise<void> {
        if (!await this.model.setPolicyType(policyType)) {
            this.#updatePolicyMenu();
        }
    }

    /**
     * Open the policy editor.
     *
     * This lets the user write a custom policy for the token.
     *
     * Version Added:
     *     9.0
     */
    #openPolicyEditor() {
        const view = new PolicyEditorView({
            model: this.model,
        });
        view.render();
        view.open();
    }

    /**
     * Update the displayed expiration date.
     */
    _updateExpires() {
        if (this.#$expires) {
            const expires = this.model.resource.get('expires');

            this.#$expires.find('time').attr('datetime', expires);
            this.$('.timesince').timesince();
        }
    }

    /**
     * Update the displayed note.
     *
     * If no note is set, then a placeholder will be shown, informing the
     * user that they can edit the note. Otherwise, their note contents
     * will be shown.
     */
    _updateNote() {
        if (this.#$note) {
            const note = this.model.resource.get('note');

            this.#$note
                .toggleClass('empty', !note)
                .text(note ? note : APITokenItemView.EMPTY_NOTE_PLACEHOLDER);
        }
    }

    /**
     * Handler for when the copy icon is clicked.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    async _onCopyClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        const token = this.$('.rb-c-config-api-tokens__value input')
            .val() as string;
        await navigator.clipboard.writeText(token);
    }

    /**
     * Handler for when the Remove action is clicked.
     *
     * This will prompt for confirmation before removing the token from
     * the server.
     */
    _onRemoveClicked() {
        showConfirmDialog({
            title: _`Are you sure you want to remove this token?`,

            body: _`
                After removing this token, any clients which are configured
                to use it will no longer be able to authenticate.
            `,
            confirmButtonText: _`Remove`,
            isDangerous: true,

            onConfirm: async () => {
                try {
                    await this.model.resource.destroy();
                } catch (e) {
                    showErrorDialog({
                        error: e,
                        title: _`Error removing the token`,
                    });

                    return false;
                }
            },
        });
    }
}


/**
 * Options for the SiteAPITokensView.
 *
 * Version Added:
 *     9.0
 */
interface SiteAPITokensViewOptions {
    /** The list of existing API tokens. */
    apiTokens: APITokenAttrs[];

    /** The name of the local site, if any. */
    localSiteName: string;

    /** The URL prefix of the local site, if any. */
    localSitePrefix: string;

    /**
     * The list of token policies available for new and existing tokens.
     *
     * Version Added:
     *     9.0
     */
    policies: APITokenPolicy[];
}


/**
 * Renders and manages a list of global or per-LocalSite API tokens.
 *
 * This will display all provided API tokens in a list, optionally labeled
 * by Local Site name. These can be removed or edited, or new tokens generated
 * through a "Generate a new API token" link.
 */
@spina
class SiteAPITokensView extends BaseView<
    undefined,
    HTMLDivElement,
    SiteAPITokensViewOptions
> {
    static className = 'rb-c-config-api-tokens';

    static template = _.template(dedent`
        <% if (name) { %>
         <div class="djblets-l-config-forms-container">
          <h3><%- name %></h3>
         </div>
        <% } %>
        <div class="api-tokens">
        </div>
    `);

    static generateTokenTemplate = _.template(dedent`
        <li class="generate-api-token djblets-c-config-forms-list__item">
         <a href="#"><%- generateText %></a>
        </li>
    `);

    static events: EventsHash = {
        'click .generate-api-token': '_onGenerateClicked'
    };

    /**********************
     * Instance variables *
     **********************/

    /** The config list. */
    apiTokensList: ConfigFormsList;

    /** The collection of items. */
    collection: APITokenItemCollection;

    /** The name of the local site, if any. */
    localSiteName: string;

    /** The URL prefix of the local site, if any. */
    localSitePrefix: string;

    /** The list view. */
    #listView: ConfigFormsListView;

    /** The "Generate a new API token" button. */
    #$generateTokenItem: JQuery;

    /**
     * Initialize the view.
     *
     * This will construct the collection of tokens and construct
     * a list for the ListView.
     *
     * Args:
     *     options (SiteAPITokensViewOptions):
     *         Options for view construction.
     */
    initialize(options: SiteAPITokensViewOptions) {
        this.localSiteName = options.localSiteName;
        this.localSitePrefix = options.localSitePrefix;

        this.collection = new APITokenItemCollection(options.apiTokens, {
            localSitePrefix: this.localSitePrefix,
            policies: options.policies,
        });

        this.apiTokensList = new ConfigFormsList({}, {
            collection: this.collection,
        });
    }

    /**
     * Render the view.
     *
     * This will render the list of API token items, along with a link
     * for generating new tokens.
     */
    protected onInitialRender() {
        this.#listView = new ConfigFormsListView({
            ItemView: APITokenItemView,
            animateItems: true,
            model: this.apiTokensList,
        });

        this.$el.html(SiteAPITokensView.template({
            name: this.localSiteName,
        }));

        this.#listView.render().$el.prependTo(this.$('.api-tokens'));

        this.#$generateTokenItem =
            $(SiteAPITokensView.generateTokenTemplate({
                generateText: _`Generate a new API token`,
            }))
            .appendTo(this.#listView.getBody());
    }

    /**
     * Handler for when the "Generate a new API token" link is clicked.
     *
     * This creates a new API token on the server and displays it in the list.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    async _onGenerateClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        const apiToken = new APIToken({
            localSitePrefix: this.localSitePrefix,
            userName: UserSession.instance.get('username')
        });

        await apiToken.save();

        this.collection.add({
            resource: apiToken,
        });

        this.#$generateTokenItem
            .detach()
            .appendTo(this.#listView.getBody());
    }
}


/**
 * Options for the APITokensView.
 *
 * Version Added:
 *     9.0
 */
export interface APITokensViewOptions {
    /** Initial contents of the tokens list. */
    apiTokens: {
        [key: string]: {
            tokens: APITokenAttrs[];
            localSitePrefix: string;
        };
    };

    /**
     * The list of token policies available for new and existing tokens.
     *
     * Version Added:
     *     9.0
     */
    policies: APITokenPolicy[];
}


/**
 * Renders and manages a page of API tokens.
 *
 * This will take the provided tokens and group them into SiteAPITokensView
 * instances, one per Local Site and one for the global tokens.
 */
@spina
export class APITokensView extends BaseView<
    undefined,
    HTMLDivElement,
    APITokensViewOptions
> {
    static template = _.template(dedent`
        <div class="api-tokens-list djblets-l-config-forms-container
                    -is-recessed -is-top-flush">
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** Initial contents of the tokens list. */
    apiTokens: {
        [key: string]: {
            tokens: APITokenAttrs[];
            localSitePrefix: string;
        };
    };

    /** The list of views for each local site. */
    #apiTokenViews: SiteAPITokensView[] = [];

    /**
     * The list of token policies available for new and existing tokens.
     *
     * Version Added:
     *     9.0
     */
    #policies: APITokenPolicy[];

    /**
     * Initialize the view.
     *
     * Args:
     *     options (APITokensViewOptions):
     *         Options for view construction.
     */
    initialize(options: APITokensViewOptions) {
        this.apiTokens = options.apiTokens;
        this.#policies = options.policies;
    }

    /**
     * Render the view.
     *
     * This will set up the elements and the list of SiteAPITokensViews.
     */
    protected onRender() {
        this.$el.html(APITokensView.template());

        const policies = this.#policies;
        const $listsContainer = this.$('.api-tokens-list');

        for (const [localSiteName, info] of Object.entries(this.apiTokens)) {
            const view = new SiteAPITokensView({
                apiTokens: info.tokens,
                localSiteName: localSiteName,
                localSitePrefix: info.localSitePrefix,
                policies: policies,
            });

            view.$el.appendTo($listsContainer);
            view.render();

            this.#apiTokenViews.push(view);
        }
    }
}
