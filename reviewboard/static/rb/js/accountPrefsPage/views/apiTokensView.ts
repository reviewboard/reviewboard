/**
 * Renders and manages a page of API tokens.
 */

import {
    type ButtonView,
    type ComponentChild,
    type DialogViewOpenOptions,
    type DialogViewOptions,
    DialogSize,
    DialogView,
    craft,
    paint,
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
import { type ListItemAction } from 'djblets/configForms/models/listItemModel';
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

    /** The date and time of last use for the token. */
    lastUsed: string | null;

    /** The name of the local site that the token is limited to. */
    localSiteName: string | null;
}


/**
 * Represents an API token in the list.
 *
 * This provides actions for editing the policy type for the token and
 * removing the token.
 */
@spina
class APITokenItem extends ConfigFormsResourceListItem<
    APITokenAttrs,
    APIToken,
    APITokenItemAttrs
> {
    static defaults: Result<Partial<APITokenItemAttrs>> = {
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

    /** The policy menu. */
    #policyMenuAction: ListItemAction;

    /**
     * Initialize the item.
     *
     * This computes the type of policy used, for display, and builds the
     * policy actions menu.
     */
    initialize(attributes?: Partial<APITokenItemAttrs>) {
        super.initialize(attributes);

        this.on('change:policyType', this._onPolicyTypeChanged, this);

        const collection = this.collection;
        const policies = collection.policies;
        const policiesMap = collection.policiesMap;
        const policyDoc = this.get('policy') || {};
        const policyType = this._guessPolicyType(policyDoc);

        this.#policyMenuAction = {
            children: [
                ...policies.map(tokenPolicy => this._makePolicyAction(
                    tokenPolicy.id,
                )),
                this._makePolicyAction(POLICY_CUSTOM, {
                    dispatchOnClick: true,
                    id: 'policy-custom',
                }),
            ],
            id: 'policy',
            label: policiesMap[policyType].name,
        };
        this.actions.unshift(this.#policyMenuAction);

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
        try {
            await this._saveAttribute('policy', policy);

            return true;
        } catch (e) {
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
        }
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

    /**
     * Create and return an action for the policy menu.
     *
     * This takes a policy type and any options to include with the
     * action definition. It will then return a suitable action,
     * for display in the policy menu.
     *
     * Args:
     *     policyType (string):
     *         The policy type to create.
     *
     *     options (object):
     *         Additional options to include in the new action definition.
     */
    _makePolicyAction(
        policyType: string,
        options?: Partial<ListItemAction>,
    ) {
        return _.defaults({
            label: this.collection.policiesMap[policyType].name,
            name: 'policy-type',
            propName: 'policyType',
            radioValue: policyType,
            type: 'radio',
        }, options);
    }

    /**
     * Handler for when the policy type changes.
     *
     * This will set the policy menu's label to that of the selected
     * policy and rebuild the menu.
     *
     * Then, if not using a custom policy, the built-in policy definition
     * matching the selected policy will be saved to the server.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the type change.
     */
    async _onPolicyTypeChanged() {
        const policyType = this.get('policyType');
        const policy = this.collection.policiesMap[policyType];

        console.assert(policy);

        this.#policyMenuAction.label = policy.name;
        this.trigger('actionsChanged');

        if (policyType !== POLICY_CUSTOM) {
            const policyDoc = policy.policyDoc;

            if (!_.isEqual(policyDoc, this.get('policy'))) {
                const prevPolicyType = this.previous('policyType');

                if (!await this.savePolicy(policyDoc)) {
                    this.set('policyType', prevPolicyType);
                }
            }
        }
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
 * Options for the PolicyEditorView.
 *
 * Version Added:
 *     9.0
 */
interface PolicyEditorViewOptions extends DialogViewOptions {
    /**
     * The previous policy type.
     *
     * This is used when restoring the value after the edit has been cancelled.
     */
    prevPolicyType: string;
}


/**
 * Provides an editor for constructing or modifying a custom policy definition.
 *
 * This renders as a modal dialog with a CodeMirror editor inside of it. The
 * editor is set to allow easy editing of a JSON payload, complete with
 * lintian checking. Only valid policy payloads can be saved to the server.
 */
@spina
class PolicyEditorView extends DialogView<
    APITokenItem,
    PolicyEditorViewOptions
> {
    static id = 'custom_policy_editor';
    static title = _`Custom Token Access Policy`;

    /**********************
     * Instance variables *
     **********************/

    /** The CodeMirror instance. */
    #codeMirror: CodeMirror.Editor = null;

    /** The previous policy type to restore if the edit is cancelled. */
    #prevPolicyType: string;

    /** The policy editor <textarea> element. */
    #textarea: HTMLTextAreaElement = null;

    /** The save buttons. */
    #saveButtons: ButtonView[];

    /**
     * Initialize the editor.
     *
     * Args:
     *     options (PolicyEditorViewOptions):
     *         Additional options for view construction.
     */
    initialize(options: Partial<PolicyEditorViewOptions>) {
        super.initialize(_.defaults(options, {
            size: DialogSize.LARGE,
        }));

        this.#prevPolicyType = options.prevPolicyType;
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

        let policy = this.model.get('policy');

        if (_.isEmpty(policy)) {
            policy = APIToken.defaultPolicies.custom;
        }

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
     *
     * The previously-selected policy type will be set on the model.
     */
    cancel() {
        this.model.set('policyType', this.#prevPolicyType);
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
                alert(_`There is a syntax error in your policy: ${e}`);

                return;
            } else {
                throw e;
            }
        }

        const model = this.model;

        if (await model.savePolicy(policy)) {
            model.set('policyType', POLICY_CUSTOM);

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
        <span class="rb-c-config-api-tokens__note"></span>
    `);

    static events: EventsHash = {
        'click .js-copy-token': '_onCopyClicked',
    };

    static actionHandlers: EventsHash = {
        'delete': '_onRemoveClicked',
        'policy-custom': '_onCustomPolicyClicked',
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
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model.resource, 'change:expires',
                      this._updateExpires);
        this.listenTo(this.model.resource, 'change:note', this._updateNote);
    }

    /**
     * Render the view.
     */
    protected onRender() {
        super.onRender();

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
     * Handler for when the "Custom" policy action is clicked.
     *
     * This displays the policy editor, allowing the user to edit a
     * custom policy for the token.
     *
     * The previously selected policy type is passed along to the editor,
     * so that the editor can revert to it if the user cancels.
     *
     * Args:
     *     e (Event):
     *         The event.
     */
    _onCustomPolicyClicked(e: Event){
        e.preventDefault();
        e.stopPropagation();

        /*
         * The drop-down menu doesn't automatically close in this case, even if
         * we don't swallow the event. This is kind of an ugly experience
         * because after the user closes the policy editor dialog, the menu
         * will still be open.
         *
         * Ideally we'd fix this inside the ConfigFormsListItemView, but the
         * way that action menus are done is very ugly, and it's all in need of
         * a rewrite to use Ink anyway.
         *
         * For now, just artificially trigger a click on the document, which
         * will be caught by the handler in
         * ConfigFormsListItemView._showActionDropdown, and remove the menu.
         */
        $(document).trigger('click');

        const view = new PolicyEditorView({
            model: this.model,
            prevPolicyType: this.model.get('policyType'),
        });
        view.render();
        view.open();
    }

    /**
     * Handler for when the Remove action is clicked.
     *
     * This will prompt for confirmation before removing the token from
     * the server.
     */
    _onRemoveClicked() {
        const onRemoveClicked = async () => {
            confirmButton.busy = true;
            cancelButton.disabled = true;

            await this.model.resource.destroy();

            dialog.close();
        }

        const cancelButton = craft<ButtonView>`
            <Ink.Button onClick=${() => dialog.close()}>
             ${_`Cancel`}
            </Ink.Button>
        `;
        const confirmButton = craft<ButtonView>`
            <Ink.Button type="danger" onClick=${() => onRemoveClicked()}>
             ${_`Remove`}
            </Ink.Button>
        `;

        const dialog = craft<DialogView>`
            <Ink.Dialog
                onClose=${() => dialog.remove()}
                title=${_`Are you sure you want to remove this token?`}>
             <Ink.Dialog.Body>
              <p>
               ${_`
                After removing this token, any clients which are configured
                to use it will no longer be able to authenticate.
               `}
              </p>
             </>
             <Ink.Dialog.PrimaryActions>
              ${cancelButton}
              ${confirmButton}
             </>
            </>
        `;

        dialog.render();
        dialog.open();
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
