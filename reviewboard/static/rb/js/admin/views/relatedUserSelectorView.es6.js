/**
 * A widget to select related users using search and autocomplete.
 */
RB.RelatedUserSelectorView = Djblets.RelatedObjectSelectorView.extend({
    className: 'related-object-selector related-user-selector',
    searchPlaceholderText: gettext('Search for users...'),

    optionTagName: 'tr',

    optionTemplate: _.template(dedent`
        <div>
         <% if (useAvatars && avatarHTML) { %><%= avatarHTML %><% } %>
         <% if (fullname) { %>
          <span class="title"><%- fullname %></span>
          <span class="description">(<%- username %>)</span>
         <% } else { %>
          <span class="title"><%- username %></span>
         <% } %>
        </div>
    `),

    selectedOptionTemplate: _.template(dedent`
        <% if (useAvatars) { %>
         <td><%= avatarHTML %></td>
        <% } %>
        <% if (fullname) { %>
         <td><%- fullname %></td>
         <td>(<%- username %>)</td>
        <% } else { %>
         <td><%- username %></td>
         <td></td>
        <% } %>
        <td>
         <a href="#" role="button"
            class="remove-item ink-i-delete-item"
            aria-label="<%- removeText %>"
            title="<%- removeText %>"
            ></a>
        </td>
    `),

    template: _.template(dedent`
        <select placeholder="<%- searchPlaceholderText %>"
                class="related-object-options"></select>
        <% if (multivalued) { %>
        <table class="related-object-selected"></table>
        <% } %>
    `),

    autoAddClose: false,

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
     *     multivalued (boolean):
     *         Whether or not the widget should allow selecting multuple
     *         values.
     *
     *     useAvatars (boolean):
     *         Whether to show avatars. Off by default.
     */
    initialize(options) {
        Djblets.RelatedObjectSelectorView.prototype.initialize.call(
            this,
            _.defaults({
                selectizeOptions: {
                    searchField: ['fullname', 'username'],
                    sortField: [
                        {field: 'fullname'},
                        {field: 'username'},
                    ],
                    valueField: 'username',
                },
            }, options));

        this._localSitePrefix = options.localSitePrefix || '';
        this._useAvatars = !!options.useAvatars;
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
        return $(this.optionTemplate(_.extend(
            { useAvatars: this._useAvatars },
            item)));
    },

    /**
     * Render an option in the selected list.
     *
     * Args:
     *     item (object):
     *         The item to render.
     *
     * Returns:
     *     string:
     *     HTML to insert into the selected items list.
     */
    renderSelectedOption(item) {
        const $item = $(this.selectedOptionTemplate(_.extend(
            {
                removeText: _`Remove user`,
                useAvatars: this._useAvatars,
            },
            item
        )));

        $item.find('.remove-item')
            .on('click', () => this._onItemRemoved($item, item));

        return $item;
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
            fullname: 1,
            'only-fields': 'avatar_html,fullname,id,username',
            'only-links': '',
            'render-avatars-at': '20',
        };

        if (query.length !== 0) {
            params.q = query;
        }

        $.ajax({
            type: 'GET',
            url: `${SITE_ROOT}${this._localSitePrefix}api/users/`,
            data: params,
            success(results) {
                callback(results.users.map(u => ({
                    avatarHTML: u.avatar_html[20],
                    fullname: u.fullname,
                    id: u.id,
                    username: u.username,
                })));
            },
            error(...args) {
                console.error('User query failed', args);
                callback();
            },
        });
    },
});
