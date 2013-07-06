/*
 * A registered review group.
 *
 * This provides some utility functions for working with an existing
 * review group.
 *
 * At the moment, this consists of marking a review group as
 * starred/unstarred.
 */
RB.ReviewGroup = RB.BaseResource.extend({
    /*
     * Marks a review group as starred or unstarred.
     */
    setStarred: function(starred, options, context) {
        var watched = RB.UserSession.instance.watchedGroups;

        if (starred) {
            watched.addImmediately(this, options, context);
        } else {
            watched.removeImmediately(this, options, context);
        }
    }
});
