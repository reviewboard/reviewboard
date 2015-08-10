(function() {


var InstalledExtensionView;


/*
 * Displays an extension in the Manage Extensions list.
 *
 * This will show information about the extension, and provide links for
 * enabling/disabling the extension, and (depending on the extension's
 * capabilities) configuring it or viewing its database.
 */
InstalledExtensionView = Backbone.View.extend({
    className: 'extension',
    tagName: 'li',

    events: {
        'click .enable-toggle': '_toggleEnableState',
        'click .reload-link': '_reloadExtensions'
    },

    template: _.template([
        '<div class="extension-header">',
        ' <h1><%- name %> <span class="version"><%- version %></span></h1>',
        ' <p class="author">',
        '  <% if (authorURL) { %>',
        '   <a href="<%- authorURL %>"><%- author %></a>',
        '  <% } else { %>',
        '   <%- author %>',
        '  <% } %>',
        ' </p>',
        '</div>',
        '<div class="description"><%- summary %></div>',
        '<% if (!loadable) { %>',
        ' <div class="extension-load-error">',
        '  <p><%- loadFailureText %></p>',
        '  <pre><%- loadError %></pre>',
        ' </div>',
        '<% } %>',
        '<ul class="object-tools">',
        ' <li><a href="#" class="enable-toggle"></a></li>',
        ' <% if (loadError) { %>',
        '  <li><a href="#" class="reload-link"><%- reloadText %></a></li>',
        ' <% } else { %>',
        '  <% if (configURL) { %>',
        '   <li><a href="<%- configURL %>" class="enabled-only changelink">',
        '       <%- configureText %></a></li>',
        '  <% } %>',
        '  <% if (dbURL) { %>',
        '   <li><a href="<%- dbURL %>" class="enabled-only changelink">',
        '       <%- databaseText %></a></li>',
        '  <% } %>',
        ' <% } %>',
        '</ul>'
    ].join('')),

    /*
     * Renders the extension in the list.
     */
    render: function() {
        this._renderTemplate();

        this.listenTo(this.model, 'change:loadable change:loadError',
                      this._renderTemplate);
        this.listenTo(this.model,
                      'change:enabled change:canEnable change:canDisable',
                      this._showEnabledState);

        return this;
    },

    /*
     * Renders the template for the extension.
     *
     * This will render the template based on the current page conditions.
     * It's called when first rendering the extension and whenever there's
     * another need to do a full re-render (such as when loading an extension
     * fails).
     */
    _renderTemplate: function() {
        this.$el.html(this.template(_.defaults({
            configureText: gettext('Configure'),
            databaseText: gettext('Database'),
            loadFailureText: gettext('This extension failed to load with the following error:'),
            reloadText: gettext('Reload')
        }, this.model.attributes)));

        if (this.model.get('loadable')) {
            this.$el.removeClass('error');
        } else {
            this.$el.addClass('error');
        }

        this._$enableToggle = this.$('.enable-toggle');
        this._$enabledToolLinks = this.$('.enabled-only');
        this._showEnabledState();
    },

    /*
     * Updates the view to reflect the current enabled state.
     *
     * The Enable/Disable link will change to reflect the state, and
     * other links (Configure and Database) will be hidden if disabled.
     */
    _showEnabledState: function() {
        var enabled = this.model.get('enabled');

        this.$el
            .removeClass(enabled ? 'disabled' : 'enabled')
            .addClass(enabled ? 'enabled' : 'disabled');

        this._$enableToggle
            .text(enabled ? gettext('Disable') : gettext('Enable'))
            .addClass(enabled ? 'disablelink' : 'enablelink')
            .removeClass(enabled ? 'enablelink' : 'disablelink')
            .setVisible((enabled && this.model.get('canDisable')) ||
                        (!enabled && this.model.get('canEnable')));
        this._$enabledToolLinks.setVisible(enabled);
    },

    /*
     * Toggles the enabled state of the extension.
     */
    _toggleEnableState: function() {
        if (this.model.get('enabled')) {
            this.model.disable();
        } else {
            this.model.enable();
        }

        return false;
    },

    _reloadExtensions: function() {
        this.trigger('reloadClicked');
        return false;
    }
});


/*
 * Displays the interface showing all installed extensions.
 *
 * This loads the list of installed extensions and displays each in a list.
 */
Djblets.ExtensionManagerView = Backbone.View.extend({
    events: {
        'click #reload-extensions': '_reloadFull'
    },

    initialize: function() {
        this._$extensions = null;
    },

    render: function() {
        this._$extensions = this.$('.extensions');

        this.listenTo(this.model, 'loaded', this._onLoaded);

        this.model.load();

        return this;
    },

    /*
     * Handler for when the list of extensions is loaded.
     *
     * Renders each extension in the list. If the list is empty, this will
     * display that there are no extensions installed.
     */
    _onLoaded: function() {
        var evenRow = false;

        this._$extensions.empty();

        if (this.model.installedExtensions.length === 0) {
            this._$extensions.append(
                $('<li/>').text(gettext('There are no extensions installed.')));
        } else {
            this.model.installedExtensions.each(function(extension) {
                var view = new InstalledExtensionView({
                    model: extension
                });

                this._$extensions.append(view.$el);
                view.$el.addClass(evenRow ? 'row2' : 'row1');
                view.render();

                this.listenTo(view, 'reloadClicked', this._reloadFull);

                evenRow = !evenRow;
            }, this);

            this._$extensions.appendTo(this.$el);
        }
    },

    /*
     * Performs a full reload of the list of extensions on the server.
     *
     * This submits our form, which is set in the template to tell the
     * ExtensionManager to do a full reload.
     */
    _reloadFull: function() {
        this.el.submit();
    }
});


})();
