/**
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
    /**
     * Return defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The default values for new model instances.
     */
    defaults() {
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

    /**
     * Return the URL for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to use when making HTTP requests.
     */
    url() {
        const url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                    'api/default-reviewers/';

        return this.isNew() ? url : `${url}${this.id}/`;
    }
});
