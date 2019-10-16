/**
 * A view for selecting a repository from a collection.
 */
RB.RepositorySelectionView = RB.CollectionView.extend({
    tagName: 'ul',
    className: 'rb-c-sidebar__items repository-selector',
    itemViewType: RB.RepositoryView,

    template: _.template(dedent`
        <li class="rb-c-sidebar__section -no-icons">
         <header class="rb-c-sidebar__section-header">
          <%- repositoriesLabel %>
         </header>
         <ul class="rb-c-sidebar__items">
          <li class="rb-c-sidebar__item">
           <div class="rb-c-sidebar__item-label">
            <div class="rb-c-search-field">
             <span class="fa fa-search"></span>
             <input class="rb-c-search-field__input"
                    placeholder="<%- filterLabel %>" />
            </div>
           </div>
          </li>
         </ul>
         <ul class="rb-c-sidebar__items
                    rb-c-new-review-request__repository-items">
        </li>
    `),

    events: {
        'input .rb-c-new-review-request__filter-field': '_onSearchChanged',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        RB.CollectionView.prototype.initialize.apply(this, arguments);

        this._selected = null;
        this._searchActive = false;

        this.listenTo(this.collection, 'selected', this._onRepositorySelected);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.RepositorySelectionView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template({
            repositoriesLabel: gettext('Repositories'),
            filterLabel: gettext('Filter'),
        }));

        this.$container = this.$('.rb-c-new-review-request__repository-items');

        this._$searchBox = this.$('.rb-c-new-review-request__filter-field');

        RB.CollectionView.prototype.render.apply(this, arguments);

        return this;
    },

    /**
     * Unselect a repository.
     */
    unselect() {
        this.views.forEach(view => {
            if (view.model === this._selected) {
                view.$el.removeClass('active');
            }
        });

        this._selected = null;

        this.trigger('selected', null);
    },

    /**
     * Callback for when an individual repository is selected.
     *
     * Ensures that the selected repository has the 'selected' class applied
     * (and no others do), and triggers the 'selected' event on the view.
     *
     * Args:
     *     item (RB.Repository):
     *         The selected repository;
     */
    _onRepositorySelected(item) {
        this._selected = item;

        this.views.forEach(view => {
            if (view.model === item) {
                view.$el.addClass('-is-active');
            } else {
                view.$el.removeClass('-is-active');
            }
        });

        this.trigger('selected', item);
    },

    /**
     * Callback for when the text in the search input changes.
     *
     * Filters the visible items.
     */
    _onSearchChanged() {
        const searchTerm = this._$searchBox.val().toLowerCase();

        this.views.forEach(view => {
            view.$el.setVisible(view.lowerName.indexOf(searchTerm) !== -1);
        });
    },
});
