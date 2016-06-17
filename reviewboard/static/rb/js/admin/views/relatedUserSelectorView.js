/**
 * A widget to select related users using search and autocomplete.
 */
RB.RelatedUserSelectorView = RB.RelatedObjectSelectorView.extend({
    _optionTemplate: _.template([
        '<div>',
        '<% if (useGravatars && avatarURL) { %>',
        ' <img src="<%- avatarURL %>">',
        '<% } %>',
        '<% if (fullname) { %>',
        ' <span class="title"><%- fullname %></span>',
        ' <span class="description">(<%- username %>)</span>',
        '<% } else { %>',
        ' <span class="title"><%- username %></span>',
        '<% } %>',
        '</div>'
    ].join('')),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     localSitePrefix (string):
     *         The URL prefix for the local site, if any.
     *
     *     useGravatars (boolean):
     *         Whether to show gravatars. Off by default.
     */
    initialize: function(options) {
        RB.RelatedObjectSelectorView.prototype.initialize.call(
            this,
            _.defaults({
                selectizeOptions: {
                    searchField: ['fullname', 'username'],
                    sortField: [
                        { field: 'fullname' },
                        { field: 'username'}
                    ],
                    valueField: 'username'
                }
            }, options));

        this._localSitePrefix = options.localSitePrefix || '';
        this._useGravatars = !!options.useGravatars;
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
    renderOption: function(item) {
        return this._optionTemplate({
            useGravatars: this._useGravatars,
            avatarURL: item.avatar_url,
            fullname: item.fullname,
            username: item.username
        });
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
    loadOptions: function(query, callback) {
        var params = {
            fullname: 1,
            'only-fields': 'avatar_url,fullname,id,username',
            'only-links': ''
        };

        if (query.length !== 0) {
            params.q = query;
        }

        $.ajax({
            type: 'GET',
            url: SITE_ROOT + this._localSitePrefix + 'api/users/',
            data: params,
            success: function(results) {
                callback(results.users);
            },
            error: function() {
                console.log('User query failed', arguments);
                callback();
            }
        });
    }
});
