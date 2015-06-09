/*
 * A registered default reviewer.
 *
 * Default reviewers auto-populate the list of reviewers for a review request
 * based on the files modified.
 *
 * The support for default reviewers is currently limited to the most basic
 * information. The lists of users, repositories and groups cannot yet be
 * provided.
 */
RB.DefaultReviewer = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            name: null,
            fileRegex: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'default_reviewer',

    attrToJsonMap: {
        fileRegex: 'file_regex'
    },

    serializedAttrs: ['fileRegex', 'name'],
    deserializedAttrs: ['fileRegex', 'name'],

    /*
     * Returns the URL to the resource.
     */
    url: function() {
        var url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/default-reviewers/';

        if (!this.isNew()) {
            url += this.id + '/';
        }

        return url;
    }
});
