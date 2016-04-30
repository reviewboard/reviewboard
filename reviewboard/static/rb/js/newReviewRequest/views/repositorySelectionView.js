/*
 * A view for selecting a repository from a collection.
 */
RB.RepositorySelectionView = RB.CollectionView.extend({
    tagName: 'ul',
    className: 'repository-selector page-sidebar-items',
    itemViewType: RB.RepositoryView,

    template: _.template([
        '<li class="section">',
        ' <div class="page-sidebar-row">',
        '  <h3 class="label"><%- repositoriesLabel %></h3>',
        ' </div>',
        ' <ul>',
        '  <li>',
        '   <div class="search-icon-wrapper">',
        '    <span class="fa fa-search"></span>',
        '    <input class="repository-search" ',
        '           placeholder="<%- filterLabel %>" />',
        '   </div>',
        '  </li>',
        ' </ul>',
        '</li>'
    ].join('')),

    events: {
        'input .repository-search': '_onSearchChanged'
    },

    /*
     * Initialize the view.
     */
    initialize: function() {
        _super(this).initialize.apply(this, arguments);

        this._selected = null;
        this._searchActive = false;

        this.listenTo(this.collection, 'selected', this._onRepositorySelected);
    },

    /*
     * Render the view.
     */
    render: function() {
        _super(this).render.apply(this, arguments);

        this.$el.prepend(this.template({
            repositoriesLabel: gettext('Repositories'),
            filterLabel: gettext('Filter')
        }));

        this._$searchIconWrapper = this.$('.search-icon-wrapper');
        this._$searchIcon = this._$searchIconWrapper.find(
            '.repository-search-icon');
        this._$searchBox = this.$('.repository-search');

        this._iconOffset = this.$el.innerWidth() -
                           this._$searchIcon.outerWidth(true);

        return this;
    },

    /*
     * Unselect a repository.
     */
    unselect: function() {
        _.each(this.views, function(view) {
            if (view.model === this._selected) {
                view.$el.removeClass('active');
            }
        }, this);

        this._selected = null;

        this.trigger('selected', null);
    },

    /*
     * Callback for when an individual repository is selected.
     *
     * Ensures that the selected repository has the 'selected' class applied
     * (and no others do), and triggers the 'selected' event on the view.
     */
    _onRepositorySelected: function(item) {
        this._selected = item;

        _.each(this.views, function(view) {
            if (view.model === item) {
                view.$el.addClass('active');
            } else {
                view.$el.removeClass('active');
            }
        });

        this.trigger('selected', item);
    },

    /*
     * Callback for when the text in the search input changes.
     *
     * Filters the visible items.
     */
    _onSearchChanged: function() {
        var searchTerm = this._$searchBox.val().toLowerCase();

        _.each(this.views, function(view) {
            view.$el.setVisible(view.lowerName.indexOf(searchTerm) !== -1);
        });
    }
});
