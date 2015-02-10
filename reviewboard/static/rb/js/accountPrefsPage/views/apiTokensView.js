(function() {


var APITokenItem,
    APITokenItemCollection,
    APITokenItemView,
    PolicyEditorView,
    SiteAPITokensView,
    POLICY_READ_WRITE = 'rw',
    POLICY_READ_ONLY = 'ro',
    POLICY_CUSTOM = 'custom',
    POLICY_LABELS = {};


POLICY_LABELS[POLICY_READ_WRITE] = gettext('Full access');
POLICY_LABELS[POLICY_READ_ONLY] = gettext('Read-only');
POLICY_LABELS[POLICY_CUSTOM] = gettext('Custom');


/*
 * Represents an API token in the list.
 *
 * This provides actions for editing the policy type for the token and
 * removing the token.
 */
APITokenItem = RB.Config.ResourceListItem.extend({
    defaults: _.defaults({
        policyType: POLICY_READ_WRITE,
        localSiteName: null,
        showRemove: true
    }, RB.Config.ResourceListItem.prototype.defaults),

    syncAttrs: ['id', 'note', 'policy', 'tokenValue'],

    /*
     * Initializes the item.
     *
     * This computes the type of policy used, for display, and builds the
     * policy actions menu.
     */
    initialize: function(options) {
        var policy,
            policyType;

        _super(this).initialize.call(this, options);

        this.on('change:policyType', this._onPolicyTypeChanged, this);

        policy = this.get('policy') || {};
        policyType = this._guessPolicyType(policy);

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

    /*
     * Creates an APIToken resource for the given attributes.
     */
    createResource: function(attrs) {
        return new RB.APIToken(_.defaults({
            userName: RB.UserSession.instance.get('username'),
            localSitePrefix: this.collection.localSitePrefix
        }, attrs));
    },

    /*
     * Sets the provided note on the token and saves it.
     */
    saveNote: function(note, options, context) {
        this._saveAttribute('note', note, options, context);
    },

    /*
     * Sets the provided policy on the token and saves it.
     */
    savePolicy: function(policy, options, context) {
        this._saveAttribute('policy', policy, options, context);
    },

    /*
     * Sets an attribute on the token and saves it.
     *
     * This is a helper function that will set an attribute on the token
     * and save it, but only after the token is ready.
     */
    _saveAttribute: function(attr, value, options, context) {
        this.resource.ready({
            ready: function() {
                this.resource.set(attr, value);
                this.resource.save(options, context);
            }
        }, this);
    },

    /*
     * Guesses the policy type for a given policy definition.
     *
     * This compares the policy against the built-in versions that
     * RB.APIToken provides. If one of them matches, the appropriate
     * policy type will be returned. Otherwise, this assumes it's a
     * custom policy.
     */
    _guessPolicyType: function(policy) {
        if (_.isEqual(policy, RB.APIToken.defaultPolicies.readOnly)) {
            return POLICY_READ_ONLY;
        } else if (_.isEqual(policy, RB.APIToken.defaultPolicies.readWrite)) {
            return POLICY_READ_WRITE;
        } else {
            return POLICY_CUSTOM;
        }
    },

    /*
     * Creates and returns an action for the policy menu.
     *
     * This takes a policy type and any options to include with the
     * action definition. It will then return a suitable action,
     * for display in the policy menu.
     */
    _makePolicyAction: function(policyType, options) {
        return _.defaults({
            label: POLICY_LABELS[policyType],
            type: 'radio',
            name: 'policy-type',
            propName: 'policyType',
            radioValue: policyType
        }, options);
    },

    /*
     * Handler for when the policy type changes.
     *
     * This will set the policy menu's label to that of the selected
     * policy and rebuild the menu.
     *
     * Then, if not using a custom policy, the built-in policy definition
     * matching the selected policy will be saved to the server.
     */
    _onPolicyTypeChanged: function() {
        var policyType = this.get('policyType'),
            newPolicy;

        this._policyMenuAction.label = POLICY_LABELS[policyType];
        this.trigger('actionsChanged');

        if (policyType === POLICY_READ_ONLY) {
            newPolicy = RB.APIToken.defaultPolicies.readOnly;
        } else if (policyType === POLICY_READ_WRITE) {
            newPolicy = RB.APIToken.defaultPolicies.readWrite;
        } else {
            return;
        }

        if (!_.isEqual(newPolicy, this.get('policy'))) {
            this.savePolicy(newPolicy);
        }
    }
});


/*
 * A collection of APITokenItems.
 *
 * This works like a standard Backbone.Collection, but can also have
 * a LocalSite URL prefix attached to it, for use in API calls in
 * APITokenItem.
 */
APITokenItemCollection = Backbone.Collection.extend({
    model: APITokenItem,

    initialize: function(models, options) {
        this.localSitePrefix = options.localSitePrefix;
    }
});


/*
 * Renders an APITokenItem to the page, and handles actions.
 *
 * This will display the information on the given token. Specifically,
 * the token value, the note, and the actions.
 *
 * This also handles deleting the token when the Remove action is clicked,
 * and displaying the policy editor when choosing a custom policy.
 */
APITokenItemView = Djblets.Config.ListItemView.extend({
    EMPTY_NOTE_PLACEHOLDER: gettext('Click to describe this token'),

    template: _.template([
        '<div class="config-api-token-value"><%- tokenValue %></div>',
        '<span class="config-api-token-note"></span>'
    ].join('')),

    actionHandlers: {
        'delete': '_onRemoveClicked',
        'policy-custom': '_onCustomPolicyClicked'
    },

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        _super(this).initialize.call(this, options);

        this._$note = null;

        this.listenTo(this.model.resource, 'change:note', this._updateNote);
    },

    /*
     * Renders the view.
     */
    render: function() {
        _super(this).render.call(this);

        this._$note = this.$('.config-api-token-note')
            .inlineEditor({
                editIconClass: 'rb-icon rb-icon-edit'
            })
            .on({
                beginEdit: _.bind(function() {
                    this._$note.inlineEditor('setValue',
                                             this.model.get('note'));
                }, this),
                complete: _.bind(function(e, value) {
                    this.model.saveNote(value);
                }, this)
            });

        this._updateNote();

        return this;
    },

    /*
     * Updates the displayed note.
     *
     * If no note is set, then a placeholder will be shown, informing the
     * user that they can edit the note. Otherwise, their note contents
     * will be shown.
     */
    _updateNote: function() {
        var note = this.model.resource.get('note');

        if (note) {
            this._$note
                .removeClass('empty')
                .text(note);
        } else {
            this._$note
                .addClass('empty')
                .text(this.EMPTY_NOTE_PLACEHOLDER);
        }
    },

    /*
     * Handler for when the "Custom" policy action is clicked.
     *
     * This displays the policy editor, allowing the user to edit a
     * custom policy for the token.
     *
     * The previously selected policy type is passed along to the editor,
     * so that the editor can revert to it if the user cancels.
     */
    _onCustomPolicyClicked: function() {
        var view = new PolicyEditorView({
            model: this.model,
            prevPolicyType: this.model.previous('policyType')
        });
        view.render();

        return false;
    },

    /*
     * Handler for when the Remove action is clicked.
     *
     * This will prompt for confirmation before removing the token from
     * the server.
     */
    _onRemoveClicked: function() {
        $('<p/>')
            .html(gettext('This will prevent clients using this token when authenticating.'))
            .modalBox({
                title: gettext('Are you sure you want to remove this token?'),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Cancel')),
                    $('<input type="button" class="danger" />')
                        .val(gettext('Remove'))
                        .click(_.bind(function() {
                            this.model.resource.destroy();
                        }, this))
                ]
            });
    }
});


/*
 * Provides an editor for constructing or modifying a custom policy definition.
 *
 * This renders as a modalBox with a CodeMirror editor inside of it. The
 * editor is set to allow easy editing of a JSON payload, complete with
 * lintian checking. Only valid policy payloads can be saved to the server.
 */
PolicyEditorView = Backbone.View.extend({
    id: 'custom_policy_editor',

    template: _.template([
        '<p><%= instructions %></p>',
        '<textarea/>'
    ].join('')),

    /*
     * Initializes the editor.
     */
    initialize: function(options) {
        this.prevPolicyType = options.prevPolicyType;

        this._codeMirror = null;
        this._$policy = null;
        this._$saveButtons = null;
    },

    /*
     * Renders the editor.
     *
     * The CodeMirror editor will be set up and configured, and then the
     * view will be placed inside a modalBox.
     */
    render: function() {
        var policy = this.model.get('policy');

        if (_.isEmpty(this.model.get('policy'))) {
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
                    .click(_.bind(function() {
                        this.save();
                        return false;
                    }, this)),
                $('<input type="button" class="btn primary save-button"/>')
                    .val(gettext('Save'))
                    .click(_.bind(function() {
                        this.save(true);
                        return false;
                    }, this))
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

    /*
     * Removes the policy editor from the page.
     */
    remove: function() {
        this.$el.modalBox('destroy');
    },

    /*
     * Cancels the editor.
     *
     * The previously-selected policy type will be set on the model.
     */
    cancel: function() {
        this.model.set('policyType', this.prevPolicyType);
    },

    /*
     * Saves the editor.
     *
     * The policy will be saved to the server for immediate use.
     */
    save: function(closeOnSave) {
        var policyStr = this._codeMirror.getValue().strip(),
            policy;

        try {
            policy = JSON.parse(policyStr);
        } catch (e) {
            alert(interpolate(
                gettext('There is a syntax error in your policy: %s'),
                [e]));

            return false;
        }

        this.model.savePolicy(policy, {
            success: function() {
                if (closeOnSave) {
                    this.remove();
                }
            },
            error: function(model, xhr) {
                if (xhr.errorPayload.err.code === 105 &&
                    xhr.errorPayload.fields.policy) {
                    alert(xhr.errorPayload.fields.policy);
                } else {
                    alert(xhr.errorPayload.err.msg);
                }
            }
        }, this);

        return false;
    },

    /*
     * Handler for when lintian checking has run.
     *
     * This will disable the save buttons if there are any lintian errors.
     */
    _onUpdateLinting: function(annotationsNotSorted) {
        this._$saveButtons.prop('disabled', annotationsNotSorted.length > 0);
    }
});


/*
 * Renders and manages a list of global or per-LocalSite API tokens.
 *
 * This will display all provided API tokens in a list, optionally labeled
 * by Local Site name. These can be removed or edited, or new tokens generated
 * through a "Generate a new API token" link.
 */
SiteAPITokensView = Backbone.View.extend({
    className: 'config-site-api-tokens',

    template: _.template([
        '<% if (name) { %>',
        ' <h3><%- name %></h3>',
        '<% } %>',
        '<div class="api-tokens box-recessed">',
        ' <div class="generate-api-token config-forms-list-item">',
        '  <a href="#"><%- generateText %></a>',
        ' </div>',
        '</div>'
    ].join('')),

    events: {
        'click .generate-api-token': '_onGenerateClicked'
    },

    /*
     * Initializes the view.
     *
     * This will construct the collection of tokens and construct
     * a list for the ListView.
     */
    initialize: function(options) {
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

    /*
     * Renders the view.
     *
     * This will render the list of API token items, along with a link
     * for generating new tokens.
     */
    render: function() {
        this._listView = new Djblets.Config.ListView({
            ItemView: APITokenItemView,
            animateItems: true,
            model: this.apiTokensList
        });

        this.$el.html(this.template({
            name: this.localSiteName,
            generateText: gettext('Generate a new API token')
        }));

        this._listView.render().$el.prependTo(this.$('.api-tokens'));

        return this;
    },

    /*
     * Handler for when the "Generate a new API token" link is clicked.
     *
     * This creates a new API token on the server and displays it in the list.
     */
    _onGenerateClicked: function() {
        var apiToken = new RB.APIToken({
            localSitePrefix: this.localSitePrefix,
            userName: RB.UserSession.instance.get('username')
        });

        apiToken.save({
            success: function() {
                this.collection.add({
                    resource: apiToken
                });
            }
        }, this);

        return false;
    }
});


/*
 * Renders and manages a page of API tokens.
 *
 * This will take the provided tokens and group them into SiteAPITokensView
 * instances, one per Local Site and one for the global tokens.
 */
RB.APITokensView = Backbone.View.extend({
    template: _.template([
        '<div class="api-tokens-list" />'
    ].join('')),

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        this.apiTokens = options.apiTokens;

        this._$listsContainer = null;
        this._apiTokenViews = [];
    },

    /*
     * Renders the view.
     *
     * This will set up the elements and the list of SiteAPITokensViews.
     */
    render: function() {
        this.$el.html(this.template());

        this._$listsContainer = this.$('.api-tokens-list');

        _.each(this.apiTokens, function(info, localSiteName) {
            var view = new SiteAPITokensView({
                localSiteName: localSiteName,
                localSitePrefix: info.localSitePrefix,
                apiTokens: info.tokens
            });

            view.$el.appendTo(this._$listsContainer);
            view.render();

            this._apiTokenViews.push(view);
        }, this);

        return this;
    }
});


})();
