(function() {


const POLICY_READ_WRITE = 'rw';
const POLICY_READ_ONLY = 'ro';
const POLICY_CUSTOM = 'custom';
const POLICY_LABELS = {
    [POLICY_READ_WRITE]: gettext('Full access'),
    [POLICY_READ_ONLY]: gettext('Read-only'),
    [POLICY_CUSTOM]: gettext('Custom')
};


/**
 * Represents an API token in the list.
 *
 * This provides actions for editing the policy type for the token and
 * removing the token.
 */
const APITokenItem = RB.Config.ResourceListItem.extend({
    defaults: _.defaults({
        policyType: POLICY_READ_WRITE,
        lastUsed: null,
        localSiteName: null,
        showRemove: true,
    }, RB.Config.ResourceListItem.prototype.defaults),

    syncAttrs: [
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
    ],

    /**
     * Initialize the item.
     *
     * This computes the type of policy used, for display, and builds the
     * policy actions menu.
     */
    initialize() {
        _super(this).initialize.apply(this, arguments);

        this.on('change:policyType', this._onPolicyTypeChanged, this);

        const policy = this.get('policy') || {};
        const policyType = this._guessPolicyType(policy);

        this._policyMenuAction = {
            id: 'policy',
            label: POLICY_LABELS[policyType],
            children: [
                this._makePolicyAction(POLICY_READ_WRITE),
                this._makePolicyAction(POLICY_READ_ONLY),
                this._makePolicyAction(POLICY_CUSTOM, {
                    id: 'policy-custom',
                    dispatchOnClick: true
                })
            ]
        };
        this.actions.unshift(this._policyMenuAction);

        this.set('policyType', policyType);
    },

    /**
     * Create an APIToken resource for the given attributes.
     *
     * Args:
     *     attrs (object):
     *         Additional attributes for the APIToken.
     */
    createResource(attrs) {
        return new RB.APIToken(_.defaults({
            userName: RB.UserSession.instance.get('username'),
            localSitePrefix: this.collection.localSitePrefix
        }, attrs));
    },

    /**
     * Set the provided expiration date on the token and save it.
     *
     * Args:
     *     expires (string):
     *         The new expiration date for the token. If this is an
     *         empty string, the token will be set to have no expiration.
     */
    saveExpires(expires) {
        this._saveAttribute('expires', expires);
    },

    /**
     * Set the provided note on the token and save it.
     *
     * Args:
     *     note (string):
     *         The new note for the token.
     */
    saveNote(note) {
        this._saveAttribute('note', note);
    },

    /**
     * Set the provided policy on the token and save it.
     *
     * Args:
     *     policy (object):
     *         The new policy for the token.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    savePolicy(policy) {
        return this._saveAttribute('policy', policy);
    },

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
    async _saveAttribute(attr, value) {
        await this.resource.ready();
        this.resource.set(attr, value);
        await this.resource.save();
    },

    /**
     * Guess the policy type for a given policy definition.
     *
     * This compares the policy against the built-in versions that
     * RB.APIToken provides. If one of them matches, the appropriate
     * policy type will be returned. Otherwise, this assumes it's a
     * custom policy.
     *
     * Args:
     *     policy (object):
     *         A policy object.
     *
     * Returns:
     *     string:
     *     The policy type enumeration corresponding to the policy.
     */
    _guessPolicyType(policy) {
        if (_.isEqual(policy, RB.APIToken.defaultPolicies.readOnly)) {
            return POLICY_READ_ONLY;
        } else if (_.isEqual(policy, RB.APIToken.defaultPolicies.readWrite)) {
            return POLICY_READ_WRITE;
        } else {
            return POLICY_CUSTOM;
        }
    },

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
    _makePolicyAction(policyType, options) {
        return _.defaults({
            label: POLICY_LABELS[policyType],
            type: 'radio',
            name: 'policy-type',
            propName: 'policyType',
            radioValue: policyType
        }, options);
    },

    /**
     * Handler for when the policy type changes.
     *
     * This will set the policy menu's label to that of the selected
     * policy and rebuild the menu.
     *
     * Then, if not using a custom policy, the built-in policy definition
     * matching the selected policy will be saved to the server.
     */
    _onPolicyTypeChanged() {
        const policyType = this.get('policyType');

        this._policyMenuAction.label = POLICY_LABELS[policyType];
        this.trigger('actionsChanged');

        let newPolicy = null;

        if (policyType === POLICY_READ_ONLY) {
            newPolicy = RB.APIToken.defaultPolicies.readOnly;
        } else if (policyType === POLICY_READ_WRITE) {
            newPolicy = RB.APIToken.defaultPolicies.readWrite;
        } else {
            return;
        }

        console.assert(newPolicy !== null);

        if (!_.isEqual(newPolicy, this.get('policy'))) {
            this.savePolicy(newPolicy);
        }
    }
});


/**
 * A collection of APITokenItems.
 *
 * This works like a standard Backbone.Collection, but can also have
 * a LocalSite URL prefix attached to it, for use in API calls in
 * APITokenItem.
 */
const APITokenItemCollection = Backbone.Collection.extend({
    model: APITokenItem,

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
     */
    initialize(models, options) {
        this.localSitePrefix = options.localSitePrefix;
    }
});


/**
 * Provides an editor for constructing or modifying a custom policy definition.
 *
 * This renders as a modalBox with a CodeMirror editor inside of it. The
 * editor is set to allow easy editing of a JSON payload, complete with
 * lintian checking. Only valid policy payloads can be saved to the server.
 */
const PolicyEditorView = Backbone.View.extend({
    id: 'custom_policy_editor',

    template: _.template([
        '<p><%= instructions %></p>',
        '<textarea/>'
    ].join('')),

    /**
     * Initialize the editor.
     *
     * Args:
     *     options (object):
     *         Additional options for view construction.
     *
     * Option Args:
     *     prevPolicyType (string):
     *         The previous policy type, to use when restoring the value after
     *         the edit has been cancelled.
     */
    initialize(options) {
        this.prevPolicyType = options.prevPolicyType;

        this._codeMirror = null;
        this._$policy = null;
        this._$saveButtons = null;
    },

    /**
     * Render the editor.
     *
     * The CodeMirror editor will be set up and configured, and then the
     * view will be placed inside a modalBox.
     *
     * Returns:
     *     PolicyEditorView:
     *     This object, for chaining.
     */
    render() {
        let policy = this.model.get('policy');

        if (_.isEmpty(policy)) {
            policy = RB.APIToken.defaultPolicies.custom;
        }

        this.$el.html(this.template({
            instructions: interpolate(
                gettext('You can limit access to the API through a custom policy. See the <a href="%s" target="_blank">documentation</a> on how to write policies.'),
                [MANUAL_URL + 'webapi/2.0/api-token-policy/'])
        }));


        this._$policy = this.$('textarea')
            .val(JSON.stringify(policy, null, '  '));

        this.$el.modalBox({
            title: gettext('Custom Token Access Policy'),
            buttons: [
                $('<input type="button"/>')
                    .val(gettext('Cancel'))
                    .click(_.bind(this.cancel, this)),
                $('<input type="button" class="save-button"/>')
                    .val(gettext('Save and continue editing'))
                    .click(() => {
                        this.save(false);
                        return false;
                    }),
                $('<input type="button" class="btn primary save-button"/>')
                    .val(gettext('Save'))
                    .click(() => {
                        this.save(true);
                        return false;
                    })
            ]
        });

        this._$saveButtons = this.$el.modalBox('buttons').find('.save-button');

        this._codeMirror = CodeMirror.fromTextArea(this._$policy[0], {
            mode: 'application/json',
            lineNumbers: true,
            lineWrapping: true,
            matchBrackets: true,
            lint: {
                onUpdateLinting: _.bind(this._onUpdateLinting, this)
            },
            gutters: ['CodeMirror-lint-markers']
        });
        this._codeMirror.focus();
    },

    /**
     * Remove the policy editor from the page.
     */
    remove() {
        this.$el.modalBox('destroy');
    },

    /**
     * Cancel the editor.
     *
     * The previously-selected policy type will be set on the model.
     */
    cancel() {
        this.model.set('policyType', this.prevPolicyType);
    },

    /**
     * Save the editor.
     *
     * The policy will be saved to the server for immediate use.
     *
     * Args:
     *     closeOnSave (boolean):
     *         Whether the editor should close after saving.
     */
    async save(closeOnSave) {
        const policyStr = this._codeMirror.getValue().strip();
        let policy;

        try {
            policy = JSON.parse(policyStr);
        } catch (e) {
            if (e instanceof SyntaxError) {
                alert(interpolate(
                    gettext('There is a syntax error in your policy: %s'),
                    [e]));

                return;
            } else {
                throw e;
            }
        }

        try {
            await this.model.savePolicy(policy);

            this.model.set('policyType', POLICY_CUSTOM);

            if (closeOnSave) {
                this.remove();
            }
        } catch (err) {
            if (err.xhr.errorPayload.err.code === 105 &&
                err.xhr.errorPayload.fields.policy) {
                alert(err.xhr.errorPayload.fields.policy);
            } else {
                alert(err.xhr.errorPayload.err.msg);
            }
        }
    },

    /**
     * Handler for when lintian checking has run.
     *
     * This will disable the save buttons if there are any lintian errors.
     *
     * Args:
     *     annotationsNotSorted (Array):
     *         An array of the linter annotations.
     */
    _onUpdateLinting(annotationsNotSorted) {
        this._$saveButtons.prop('disabled', annotationsNotSorted.length > 0);
    }
});


/**
 * Renders an APITokenItem to the page, and handles actions.
 *
 * This will display the information on the given token. Specifically,
 * the token value, the note, the expiration date and the actions.
 *
 * This also handles deleting the token when the Remove action is clicked,
 * and displaying the policy editor when choosing a custom policy.
 */
const APITokenItemView = Djblets.Config.ListItemView.extend({
    EMPTY_NOTE_PLACEHOLDER: gettext('Click to describe this token'),

    template: _.template(gettext`
        <div class="rb-c-config-api-tokens__main">
         <div class="rb-c-config-api-tokens__value">
          <input readonly="readonly" value="<%- tokenValue %>">
         </div>
         <span class="fa fa-clipboard js-copy-token" title="Copy to clipboard"></span>
        </div>
        <div class="rb-c-config-api-tokens__info">
         <% if (deprecated) { %>
          <p class="rb-c-config-api-tokens__deprecation-notice">
           This token uses a deprecated format. You should remove it and
           generate a new one.
          </p>
         <% } %>
         <% if (expired) { %>
          <p class="rb-c-config-api-tokens__token-state -is-expired">
           Expired <time class="timesince" datetime="<%= expires %>"></time>.
          </p>
         <% } else if (valid) { %>
          <% if (lastUsed) { %>
           <p class="rb-c-config-api-tokens__usage -has-last-used">
            Last used
            <time class="timesince" datetime="<%= lastUsed %>"></time>.
           </p>
          <% } else { %>
           <p class="rb-c-config-api-tokens__usage">Never used.</p>
          <% } %>
          <% if (expires) { %>
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
    `),

    events: {
        'click .js-copy-token': '_onCopyClicked',
    },

    actionHandlers: {
        'delete': '_onRemoveClicked',
        'policy-custom': '_onCustomPolicyClicked'
    },

    /**
     * Initialize the view.
     */
    initialize() {
        _super(this).initialize.apply(this, arguments);

        this._$expires = null;
        this._$note = null;
        this._$tokenState = null;

        this.listenTo(this.model.resource, 'change:expires', this._updateExpires);
        this.listenTo(this.model.resource, 'change:note', this._updateNote);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     APITokenItemView:
     *     This object, for chaining.
     */
    render() {
        _super(this).render.call(this);

        this._$tokenState = this.$('.rb-c-config-api-tokens__token-state');
        this._$expires = this._$tokenState
            .not('.is-expired, .is-invalid')
            .find('span');

        this._$note = this.$('.rb-c-config-api-tokens__note')
            .inlineEditor({
                editIconClass: 'rb-icon rb-icon-edit'
            })
            .on({
                beginEdit: () => this._$note.inlineEditor(
                    'setValue', this.model.get('note')),
                complete: (e, value) => this.model.saveNote(value)
            });

        /**
         * Use tomorrow as the minimum date that the expiration date
         * can be set to.
         */
        const tomorrow = moment().local().add(1, 'days');
        const expires = moment(this.model.get('expires')).local();

        const expiresView = new RB.DateInlineEditorView({
            el: this._$expires[0],
            descriptorText: 'Expires ',
            formatResult: value => {
                if (value) {
                    value = moment(value).local().startOf('day').format();

                    return (dedent`
                        Expires
                        <time class="timesince" datetime="${value}"></time>.
                    `);
                } else {
                    return 'Never expires.';
                }
            },
            minDate: tomorrow.format('YYYY-MM-DD'),
            rawValue: expires.format('YYYY-MM-DD'),
        });
        expiresView.render();

        this.listenTo(expiresView, 'complete', (value) => {
            // Set the expiration time to midnight local time.
            value = value ? moment(value).local().startOf('day').format() :
                    '';

            this.model.saveExpires(value);
        });

        this._updateExpires();
        this._updateNote();

        return this;
    },

    /**
     * Return the parent element for item actions.
     *
     * Returns:
     *     jQuery:
     *     The element to attach the actions to.
     */
    getActionsParent() {
        return this.$('.rb-c-config-api-tokens__actions');
    },

    /**
     * Return additional rendering context.
     *
     * Returns:
     *     object:
     *     Additional rendering context.
     */
    getRenderContext() {
        const expires = this.model.get('expires');

        return {
            expiresTimeHTML:
                `<time class="timesince" datetime="${expires}"></time>`,
        };
    },

    /**
     * Update the displayed expiration date.
     */
     _updateExpires() {
        if (this._$expires) {
            const expires = this.model.resource.get('expires');

            this._$expires.find('time').attr('datetime', expires);
            this.$('.timesince').timesince();
        }
    },

    /**
     * Update the displayed note.
     *
     * If no note is set, then a placeholder will be shown, informing the
     * user that they can edit the note. Otherwise, their note contents
     * will be shown.
     */
    _updateNote() {
        if (this._$note) {
            const note = this.model.resource.get('note');

            this._$note
                .toggleClass('empty', !note)
                .text(note ? note : this.EMPTY_NOTE_PLACEHOLDER);
        }
    },

    /**
     * Handler for when the copy icon is clicked.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _onCopyClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.$('.rb-c-config-api-tokens__value input')
            .focus()
            .select();
        document.execCommand('copy');
    },

    /**
     * Handler for when the "Custom" policy action is clicked.
     *
     * This displays the policy editor, allowing the user to edit a
     * custom policy for the token.
     *
     * The previously selected policy type is passed along to the editor,
     * so that the editor can revert to it if the user cancels.
     *
     * Returns:
     *     boolean:
     *     false, for use as a jQuery event handler.
     */
    _onCustomPolicyClicked() {
        const view = new PolicyEditorView({
            model: this.model,
            prevPolicyType: this.model.get('policyType'),
        });
        view.render();

        return false;
    },

    /**
     * Handler for when the Remove action is clicked.
     *
     * This will prompt for confirmation before removing the token from
     * the server.
     */
    _onRemoveClicked() {
        $('<p/>')
            .html(gettext('This will prevent clients using this token when authenticating.'))
            .modalBox({
                title: gettext('Are you sure you want to remove this token?'),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Cancel')),
                    $('<input type="button" class="danger" />')
                        .val(gettext('Remove'))
                        .click(() => this.model.resource.destroy())
                ]
            });
    }
});


/**
 * Renders and manages a list of global or per-LocalSite API tokens.
 *
 * This will display all provided API tokens in a list, optionally labeled
 * by Local Site name. These can be removed or edited, or new tokens generated
 * through a "Generate a new API token" link.
 */
const SiteAPITokensView = Backbone.View.extend({
    className: 'rb-c-config-api-tokens',

    template: _.template(dedent`
        <% if (name) { %>
         <div class="djblets-l-config-forms-container">
          <h3><%- name %></h3>
         </div>
        <% } %>
        <div class="api-tokens">
        </div>
    `),

    generateTokenTemplate: _.template(dedent`
        <li class="generate-api-token djblets-c-config-forms-list__item">
         <a href="#"><%- generateText %></a>
        </li>
    `),

    events: {
        'click .generate-api-token': '_onGenerateClicked'
    },

    /**
     * Initialize the view.
     *
     * This will construct the collection of tokens and construct
     * a list for the ListView.
     *
     * Args:
     *     options (object):
     *         Options for view construction.
     *
     * Option Args:
     *     localSiteName (string):
     *         The name of the local site, if any.
     *
     *     localSitePrefix (string):
     *         The URL prefix of the local site, if any.
     */
    initialize(options) {
        this.localSiteName = options.localSiteName;
        this.localSitePrefix = options.localSitePrefix;

        this.collection = new APITokenItemCollection(options.apiTokens, {
            localSitePrefix: this.localSitePrefix
        });

        this.apiTokensList = new Djblets.Config.List({}, {
            collection: this.collection
        });

        this._listView = null;
    },

    /**
     * Render the view.
     *
     * This will render the list of API token items, along with a link
     * for generating new tokens.
     *
     * Returns:
     *     SiteAPITokensView:
     *     This object, for chaining.
     */
    render() {
        this._listView = new Djblets.Config.ListView({
            ItemView: APITokenItemView,
            animateItems: true,
            model: this.apiTokensList
        });

        this.$el.html(this.template({
            name: this.localSiteName,
        }));

        this._listView.render().$el.prependTo(this.$('.api-tokens'));

        this._$generateTokenItem =
            $(this.generateTokenTemplate({
                generateText: _`Generate a new API token`,
            }))
            .appendTo(this._listView.getBody());

        return this;
    },

    /**
     * Handler for when the "Generate a new API token" link is clicked.
     *
     * This creates a new API token on the server and displays it in the list.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    async _onGenerateClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        const apiToken = new RB.APIToken({
            localSitePrefix: this.localSitePrefix,
            userName: RB.UserSession.instance.get('username')
        });

        await apiToken.save();

        this.collection.add({
            resource: apiToken,
        });

        this._$generateTokenItem
            .detach()
            .appendTo(this._listView.getBody());
    },
});


/**
 * Renders and manages a page of API tokens.
 *
 * This will take the provided tokens and group them into SiteAPITokensView
 * instances, one per Local Site and one for the global tokens.
 */
RB.APITokensView = Backbone.View.extend({
    template: _.template(dedent`
        <div class="api-tokens-list djblets-l-config-forms-container
                    -is-recessed -is-top-flush">
        </div>
    `),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for view construction.
     *
     * Option Args:
     *     apiTokens (Array of object):
     *         Initial contents of the tokens list.
     */
    initialize(options) {
        this.apiTokens = options.apiTokens;

        this._$listsContainer = null;
        this._apiTokenViews = [];
    },

    /**
     * Render the view.
     *
     * This will set up the elements and the list of SiteAPITokensViews.
     *
     * Returns:
     *     RB.APITokensView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template());

        this._$listsContainer = this.$('.api-tokens-list');

        for (let [localSiteName, info] of Object.entries(this.apiTokens)) {
            const view = new SiteAPITokensView({
                localSiteName: localSiteName,
                localSitePrefix: info.localSitePrefix,
                apiTokens: info.tokens
            });

            view.$el.appendTo(this._$listsContainer);
            view.render();

            this._apiTokenViews.push(view);
        }

        return this;
    }
});


})();
