/**
 * A widget to select related objects using search and autocomplete.
 *
 * This is particularly useful for models where there can be a ton of rows in
 * the database. The built-in admin widgets provide a pretty poor
 * experience--either populating the list with the entire contents of the
 * table, which is super slow, or just listing PKs, which isn't usable.
 */
RB.RelatedObjectSelectorView = Backbone.View.extend({
    className: 'related-object-select',

    _template: _.template([
        '<select placeholder="<%- searchPlaceholderText %>" ',
        '        class="related-object-options"></select>',
        '<ul class="related-object-selected"></ul>'
    ].join('')),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     $input (jQuery):
     *         The ``<input>`` element which should be populated with the list
     *         of selected item PKs.
     *
     *     initialOptions (Array of object):
     *         The initially selected options.
     *
     *     selectizeOptions (object):
     *          Additional options to pass in to $.selectize.
     */
    initialize: function(options) {
        this.options = options;
        this._$input = options.$input;
        this._selectizeOptions = options.selectizeOptions;
        this._selectedIDs = {};
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.RelatedObjectSelectorView:
     *     This object, for chaining.
     */
    render: function() {
        var self = this,
            i,
            item;

        this.$el.html(this._template({
            searchPlaceholderText: gettext('Search for users...')
        }));

        this._$selected = this.$('.related-object-selected');

        this.$('select')
            .selectize(_.defaults(this._selectizeOptions, {
                copyClassesToDropdown: true,
                dropdownParent: 'body',
                preload: 'focus',
                render: {
                    item: function() {
                        // Always return an empty string
                        return '';
                    },
                    option: _.bind(this.renderOption, this)
                },
                load: function(query, callback) {
                    self.loadOptions(query, function(data) {
                        callback(data.filter(function(item) {
                            return !self._selectedIDs.hasOwnProperty(item.id);
                        }));
                    });
                },
                onChange: function(selected) {
                    if (selected) {
                        self._onItemSelected(this.options[selected], true);
                        this.removeOption(selected);
                    }

                    this.clear();
                }
            }));

        for (i = 0; i < this.options.initialOptions.length; i++) {
            item = this.options.initialOptions[i];
            this._onItemSelected(item, false);
        }

        this._$input.after(this.$el);
        return this;
    },

    /**
     * Update the "official" ``<input>`` element.
     *
     * This copies the list of selected item IDs into the form field which will
     * be submitted.
     */
    _updateInput: function() {
        this._$input.val(_.keys(this._selectedIDs).join(','));
    },

    /**
     * Callback for when an item is selected.
     *
     * Args:
     *     item (object):
     *         The newly-selected item.
     *
     *     addToInput (boolean):
     *         Whether the ID of the item should be added to the ``<input>``
     *         field.
     *
     *         This will be ``false`` when populating the visible list from the
     *         value of the form field when the page is initially loaded, and
     *         ``true`` when adding items interactively.
     */
    _onItemSelected: function(item, addToInput) {
        var $li = $('<li>').html(this.renderOption(item)),
            $items = this._$selected.children(),
            text = $li.text(),
            attached = false,
            compareStrings = RB.RelatedObjectSelectorView.compareStrings,
            i,
            $item;

        $('<span class="remove-item fa fa-close">')
            .click(_.bind(this._onItemRemoved, this, $li, item))
            .appendTo($li);

        for (i = 0; i < $items.length; i++) {
            $item = $items.eq(i);

            if (compareStrings($item.text(), text) > 0) {
                $item.before($li);
                attached = true;
                break;
            }
        }

        if (!attached) {
            $li.appendTo(this._$selected);
        }

        this._selectedIDs[item.id] = item;

        if (addToInput) {
            this._updateInput();
        }
    },

    /**
     * Callback for when an item is removed from the list.
     *
     * Args:
     *     $li (jQuery):
     *         The element representing the item in the selected list.
     *
     *     item (object):
     *         The item being removed.
     */
    _onItemRemoved: function($li, item) {
        $li.remove();
        delete this._selectedIDs[item.id];
        this._updateInput();
    },

    /**
     * Render an option in the drop-down menu.
     *
     * This should be overridden in order to render type-specific data.
     *
     * Args:
     *     item (object):
     *         The item to render.
     *
     * Returns:
     *     string:
     *     HTML to insert into the drop-down menu.
     */
    renderOption: function(/* item */) {
        return '';
    },

    /**
     * Load options from the server.
     *
     * This should be overridden in order to make whatever API requests are
     * necessary.
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
        callback();
    }
}, {
    /**
     * Compare two strings.
     *
     * This method optimistically uses String.localeCompare, falling back to
     * the operator-based comparison for browsers that don't implement it.
     *
     * Args:
     *     a (string):
     *         The first string to compare.
     *
     *     b (string):
     *         The second string to compare.
     *
     * Returns:
     *     number:
     *     A number which is negative if ``a`` should be sorted before ``b``, 0
     *     if they are equal, or positive if ``a`` should be sorted after
     *     ``b``.
     */
    compareStrings: function(a, b) {
        if (String.prototype.localeCompare !== undefined) {
            return a.localeCompare(b);
        } else {
            return (a === b ? 0 : a < b ? -1 : 1);
        }
    }
});
