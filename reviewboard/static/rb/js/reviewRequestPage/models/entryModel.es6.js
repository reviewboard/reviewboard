/**
 * An entry on the review request page.
 *
 * This represents entries on the review request page, such as reviews and
 * review request changes. It stores common state used by all entries.
 *
 * This is meant to be subclassed to handle parsing of custom content or
 * storing custom state, but can be used as-is for simple entries.
 *
 * Model Attributes:
 *     addedTimestamp (Date):
 *         The date/time the entry was added.
 *
 *     collapsed (boolean):
 *         Whether this entry is in a collapsed state.
 *
 *     page (RB.ReviewRequestPage):
 *         The page that owns this entry.
 *
 *     reviewRequestEditor (RB.ReviewRequestEditor):
 *         The review request editor managing state on the page.
 *
 *     typeID (string):
 *         The type of this entry, corresponding to a entry type ID that's
 *         been registered server-side.
 *
 *     updatedTimestamp (Date):
 *         The date/time the entry was last updated.
 */
RB.ReviewRequestPage.Entry = Backbone.Model.extend({
    defaults: {
        addedTimestamp: null,
        collapsed: false,
        page: null,
        reviewRequestEditor: null,
        typeID: null,
        updatedTimestamp: null,
    },

    /**
     * Parse attributes for the model.
     *
     * Args:
     *     attrs (object):
     *         The attributes provided when constructing the model instance.
     *
     * Returns:
     *     object:
     *     The resulting attributes used for the model instance.
     */
    parse(attrs) {
        return {
            id: attrs.id,
            collapsed: attrs.collapsed,
            addedTimestamp: moment.utc(attrs.addedTimestamp).toDate(),
            updatedTimestamp: moment.utc(attrs.updatedTimestamp).toDate(),
            typeID: attrs.typeID,
            reviewRequestEditor: attrs.reviewRequestEditor,
        };
    },

    /**
     * Handle operations before applying an update from the server.
     *
     * This can be overridden by entries to store state or before cleanup
     * before reloading and re-rendering the HTML from the server.
     *
     * Subclasses do not need to call the parent method.
     *
     * Args:
     *     entryData (object):
     *         The metadata provided by the server in the update.
     */
    beforeApplyUpdate(entryData) {
    },

    /**
     * Handle operations after applying an update from the server.
     *
     * This can be overridden by entries to restore state or perform other
     * post-update tasks after reloading and re-rendering the HTML from the
     * server.
     *
     * Subclasses do not need to call the parent method.
     *
     * Args:
     *     entryData (object):
     *         The metadata provided by the server in the update.
     */
    afterApplyUpdate(entryData) {
    },

    /**
     * Watch for updates to this entry.
     *
     * The entry will be checked for updates at least once every ``periodMS``
     * milliseconds.
     *
     * Args:
     *     periodMS (number):
     *         The frequency at which the updates should be polled. Updates
     *         will be checked at least this often.
     */
    watchUpdates(periodMS) {
        this.get('page').watchEntryUpdates(this, periodMS);
    },

    /**
     * Stop watching for updates to this entry.
     */
    stopWatchingUpdates() {
        this.get('page').stopWatchingEntryUpdates(this);
    },
});
