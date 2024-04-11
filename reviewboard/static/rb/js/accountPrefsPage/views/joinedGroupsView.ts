/**
 * UI for managing a user's group memberships.
 */

import {
    type EventsHash,
    type Result,
    BaseView,
    spina,
} from '@beanbag/spina';

import {
    ConfigFormsList,
    ConfigFormsListItem,
    ConfigFormsListItemView,
    ConfigFormsListView,
} from 'djblets/configForms';
import {
    type ListItemAttrs,
} from 'djblets/configForms/models/listItemModel';

import {
    ReviewGroup,
    UserSession,
} from 'reviewboard/common';


/**
 * Attributes for the GroupMembershipItem model.
 *
 * Version Added:
 *     8.0
 */
interface GroupMembershipItemAttrs extends ListItemAttrs {
    /** The display name of the group. */
    displayName: string | null;

    /** The name of the group. */
    groupName: string | null;

    /** Whether the user has joined the group. */
    joined: boolean;

    /** The name of the local site that the group is in. */
    localSiteName: string | null;

    /** The URL to the group page. */
    url: string | null;
}

/**
 * An item representing the user's membership with a group.
 *
 * This keeps track of the group's information and the membership state
 * for the user. It also allows changing that membership.
 *
 * This provides two actions: 'Join', and 'Leave'.
 */
@spina
class GroupMembershipItem extends ConfigFormsListItem<
    GroupMembershipItemAttrs
> {
    static defaults: Result<Partial<GroupMembershipItemAttrs>> = {
        displayName: null,
        groupName: null,
        joined: false,
        localSiteName: null,
        showRemove: false,
        url: null,
    };

    /**********************
     * Instance variables *
     **********************/

    /** The group API resource. */
    group: ReviewGroup;

    /**
     * Initialize the item.
     *
     * The item's name and URL will be taken from the serialized group
     * information, and a proxy ReviewGroup will be created to handle
     * membership.
     */
    initialize(attrs: Partial<GroupMembershipItemAttrs>) {
        super.initialize(attrs);

        const name = this.get('name');
        const localSiteName = this.get('localSiteName');

        this.set({
            editURL: this.get('url'),
            text: name,
        });

        this.group = new ReviewGroup({
            id: this.get('reviewGroupID'),
            localSitePrefix: (localSiteName ? `s/${localSiteName}/` : ''),
            name: name,
        });

        this.on('change:joined', this.#updateActions, this);
        this.#updateActions();
    }

    /**
     * Join the group.
     *
     * This will add the user to the group, and set the 'joined' property
     * to true upon completion.
     */
    async joinGroup() {
        await this.group.addUser(UserSession.instance.get('username'));
        this.set('joined', true);
    }

    /**
     * Leave the group.
     *
     * This will remove the user from the group, and set the 'joined' property
     * to false upon completion.
     */
    async leaveGroup() {
        await this.group.removeUser(UserSession.instance.get('username'));
        this.set('joined', false);
    }

    /**
     * Update the list of actions.
     *
     * This will replace the existing action, if any, with a new action
     * allowing the user to join or leave the group, depending on their
     * current membership status.
     */
    #updateActions() {
        if (this.get('joined')) {
            this.actions = [{
                id: 'leave',
                label: _`Leave`,
            }];
        } else {
            this.actions = [{
                id: 'join',
                label: _`Join`,
            }];
        }

        this.trigger('actionsChanged');
    }
}


/**
 * Provides UI for showing a group membership.
 *
 * This will display the group information and provide buttons for
 * the Join/Leave actions.
 */
@spina
class GroupMembershipItemView extends ConfigFormsListItemView<
    GroupMembershipItem
> {
    static actionHandlers: EventsHash = {
        'join': '_onJoinClicked',
        'leave': '_onLeaveClicked',
    };

    static template = _.template(dedent`
        <span class="config-group-name">
         <a href="<%- editURL %>"><%- text %></a>
        </span>
        <span class="config-group-display-name"><%- displayName %></span>
    `);

    /**
     * Handler for when Join is clicked.
     *
     * Tells the model to join the group.
     */
    _onJoinClicked() {
        this.model.joinGroup();
    }

    /**
     * Handler for when Leave is clicked.
     *
     * Tells the model to leave the group.
     */
    _onLeaveClicked() {
        this.model.leaveGroup();
    }
}


/**
 * Options for the SiteGroupsView.
 *
 * Version Added:
 *     8.0
 */
interface SiteGroupsViewOptions {
    /** Data for the groups in the site. */
    groups: GroupMembershipItemAttrs[];

    /** The name of the local site. */
    name: string;
}


/**
 * Displays a list of group membership items, globally or for a Local Site.
 *
 * If displaying for a Local Site, then the name of the site will be shown
 * before the list.
 *
 * Each group in the list will be shown as an item with Join/Leave buttons.
 *
 * The list of groups are filterable. When filtering, if there are no groups
 * that match the filter, then the whole view will be hidden.
 */
@spina
class SiteGroupsView extends BaseView<
    undefined,
    HTMLDivElement,
    SiteGroupsViewOptions
> {
    static template = _.template(dedent`
        <% if (name) { %>
         <div class="djblets-l-config-forms-container">
          <h3><%- name %></h3>
         </div>
        <% } %>
        <div class="groups"></div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The list of groups in the local site. */
    groupList: ConfigFormsList;

    /** The name of the local site. */
    name: string;

    /**
     * Initialize the view.
     *
     * This will create a list for all groups in this view.
     *
     * Args:
     *     options (object):
     *         Options for view construction.
     *
     * Option Args:
     *     name (string):
     *         The name of the local site, if any.
     */
    initialize(options: SiteGroupsViewOptions) {
        this.name = options.name;
        this.collection = new RB.FilteredCollection(null, {
            collection: new Backbone.Collection(options.groups, {
                model: GroupMembershipItem,
            }),
        });
        this.groupList = new ConfigFormsList({}, {
            collection: this.collection,
        });
    }

    /**
     * Render the view.
     */
    protected onRender() {
        const listView = new ConfigFormsListView({
            ItemView: GroupMembershipItemView,
            model: this.groupList,
        });

        this.$el.html(SiteGroupsView.template({
            name: this.name,
        }));

        listView.render();
        listView.$el.appendTo(this.$('.groups'));
    }

    /**
     * Filter the list of groups by name.
     *
     * If no groups are found, then the view will hide itself.
     *
     * Args:
     *     name (string):
     *         The group name to search for.
     */
    filterBy(name: string) {
        this.collection.setFilters({
            'name': name,
        });

        this.$el.toggle(this.collection.length > 0);
    }
}


/**
 * Options for the JoinedGroupsView.
 *
 * Version Added:
 *     8.0
 */
interface JoinedGroupsViewOptions {
    /** The initial set of groups, grouped by local site. */
    groups: Record<string, GroupMembershipItemAttrs[]>;
}


/**
 * Provides UI for managing a user's group memberships.
 *
 * All accessible groups will be shown to the user, sectioned by
 * Local Site. This list is filterable through a search box at the top of
 * the view.
 *
 * Each group entry provides a button for joining or leaving the group,
 * allowing users to manage their memberships.
 */
@spina
export class JoinedGroupsView extends BaseView<
    undefined,
    HTMLDivElement,
    JoinedGroupsViewOptions
> {
    static template = dedent`
        <div class="djblets-l-config-forms-container">
         <div class="rb-c-search-field">
          <span class="fa fa-search"></span>
          <input class="rb-c-search-field__input" type="search">
         </div>
        </div>
        <div class="group-lists"></div>
    `;

    static events: EventsHash = {
        'change .rb-c-search-field__input': '_onGroupSearchChanged',
        'keyup .rb-c-search-field__input': '_onGroupSearchChanged',
        'submit': '_onSubmit',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The initial set of groups, grouped by local site. */
    groups: Record<string, GroupMembershipItemAttrs[]>;

    /** The set of list views for each local site. */
    #groupViews: SiteGroupsView[] = [];

    /** The search box. */
    #$search: JQuery = null;

    /** The most recently-run search string. */
    #searchText: string | null = null;

    /*
     * Initialize the view.
     *
     * Args:
     *     options (JoinedGroupsViewOptions):
     *         Options for view construction.
     */
    initialize(options: JoinedGroupsViewOptions) {
        this.groups = options.groups;
    }

    /**
     * Render the view.
     *
     * This will set up the elements and the list of SiteGroupsViews.
     */
    protected onRender() {
        this.$el.html(JoinedGroupsView.template);

        const $listsContainer = this.$('.group-lists');
        this.#$search = this.$('.rb-c-search-field__input');

        for (const [localSiteName, groups] of Object.entries(this.groups)) {
            if (groups.length > 0) {
                const view = new SiteGroupsView({
                    groups: groups,
                    name: localSiteName,
                });

                view.$el.appendTo($listsContainer);
                view.render();

                this.#groupViews.push(view);
            }
        }
    }

    /**
     * Handler for when the search box changes.
     *
     * This will instruct the SiteGroupsViews to filter their contents
     * by the text entered into the search box.
     */
    _onGroupSearchChanged() {
        const text = this.#$search.val() as string;

        if (text !== this.#searchText) {
            this.#searchText = text;
            this.#groupViews.forEach(view => view.filterBy(this.#searchText));
        }
    }

    /**
     * Prevent form submission.
     *
     * This form live updates based on the content of the <input> field and
     * submitting it will result in a CSRF error.
     *
     * Args:
     *     e (Event):
     *         The form submission event.
     */
    _onSubmit(e: Event) {
        e.preventDefault();
    }
}
