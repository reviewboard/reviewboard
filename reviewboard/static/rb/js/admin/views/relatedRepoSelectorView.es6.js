(function() {

const optionTemplate = _.template(dedent`
    <div>
     <span class="title"><%- name %></span>
    </div>
`);


/**
 * A widget to select related repositories using search and autocomplete.
 */
RB.RelatedRepoSelectorView = Djblets.RelatedObjectSelectorView.extend({
    searchPlaceholderText: gettext('Search for repositories...'),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     localSitePrefix (string):
     *         The URL prefix for the Local Site, if any.
     *
     *     multivalued (boolean):
     *         Whether or not the widget should allow selecting multiple
     *         values.
     */
    initialize(options) {
        Djblets.RelatedObjectSelectorView.prototype.initialize.call(
            this,
            _.defaults({
                selectizeOptions: {
                    searchField: ['name'],
                    sortField: [
                        {field: 'name'},
                    ],
                    valueField: 'name',
                }
            }, options));

        this._localSitePrefix = options.localSitePrefix || '';
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
            'only-fields': 'name,id',
        };

        if (query.length !== 0) {
            params.q = query;
        }

        $.ajax({
            type: 'GET',
            url: `${SITE_ROOT}${this._localSitePrefix}api/repositories/`,
            data: params,
            success: results => {
                callback(results.repositories.map(u => ({
                    name: u.name,
                    id: u.id,
                })));
            },
            error: (...args) => {
                console.error('Repository query failed', args);
                callback();
            },
        });
    },
});


})();
