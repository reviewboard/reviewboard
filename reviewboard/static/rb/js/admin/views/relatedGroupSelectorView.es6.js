(function() {


const optionTemplate = _.template(dedent`
    <div>
     <span class="title"><%- name %> : <%- display_name %></span>
    </div>
`);


/**
 * A widget to select related groups using search and autocomplete.
 */
RB.RelatedGroupSelectorView = Djblets.RelatedObjectSelectorView.extend({
    searchPlaceholderText: gettext('Search for groups...'),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     localSitePrefix (string, optional):
     *         The URL prefix for the local site, if any.
     *
     *     multivalued (boolean, optional):
     *         Whether or not the widget should allow selecting multuple
     *         values.
     *
     *     inviteOnly (boolean, optional):
     *         Whether or not to limit results to accessible review groups
     *         that are invite-only.
     *
     *     showInvisible (boolean, optional):
     *         Whether to include accessible invisible review groups in the
     *         results.
     *
     *         Version Added:
     *             5.0.6
     */
    initialize(options) {
        Djblets.RelatedObjectSelectorView.prototype.initialize.call(
            this,
            _.defaults({
                selectizeOptions: {
                    searchField: ['name', 'display_name'],
                    sortField: [
                        {field: 'name'},
                        {field: 'display_name'},
                    ],
                    valueField: 'name',
                }
            }, options));

        this._localSitePrefix = options.localSitePrefix || '';
        this._inviteOnly = options.inviteOnly;
        this._showInvisible = options.showInvisible;
    },

    /**
     * Render an option in the drop-down menu.
     *
     * Args:
     *     item (object):
     *         The item to render.
     *
     * Returns:
     *     string:
     *     HTML to insert into the drop-down menu.
     */
    renderOption(item) {
        return optionTemplate(item);
    },

    /**
     * Load options from the server.
     *
     * Args:
     *     query (string):
     *         The string typed in by the user.
     *
     *     callback (function):
     *         A callback to be called once data has been loaded. This should
     *         be passed an array of objects, each representing an option in
     *         the drop-down.
     */
    loadOptions(query, callback) {
        const params = {
            'only-fields': 'invite_only,name,display_name,id',
            displayname: 1,
        };

        if (query.length !== 0) {
            params.q = query;
        }

        if (this._inviteOnly) {
            params['invite-only'] = '1';
        }

        if (this._showInvisible) {
            params['show-invisible'] = '1';
        }

        $.ajax({
            type: 'GET',
            url: `${SITE_ROOT}${this._localSitePrefix}api/groups/`,
            data: params,
            success: results => {
                callback(results.groups.map(u => ({
                    name: u.name,
                    display_name: u.display_name,
                    id: u.id,
                    invite_only: u.invite_only
                })));
            },
            error: (...args) => {
                console.error('Group query failed', args);
                callback();
            },
        });
    },
});


})();
