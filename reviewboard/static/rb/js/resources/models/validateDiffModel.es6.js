/**
 * A resource for checking whether a diff will work.
 *
 * This is meant to be used as a sort of throwaway object, since a POST to the
 * diff validation resource does not actually create any state on the server.
 *
 * To use this, create an instance of the model, and set the diff and repository
 * attributes. The parentDiff and basedir attributes can also be set, in the
 * cases where the diff file requires a parent diff, and when the given
 * repository requires base directory information, respectively.
 *
 * Once these are set, calling save() will do a server-side check to make sure
 * that the supplied files parse correctly, and that the source revisions are
 * present in the given repository. save's 'success' and 'error' callbacks can
 * be used to act upon this information.
 */
RB.ValidateDiffModel = RB.Diff.extend({
    defaults: _.defaults({
        repository: null,
        localSitePrefix: ''
    }, _.result(RB.Diff.prototype, 'defaults')),

    serializedAttrs: [
        'repository'
    ].concat(RB.Diff.prototype.serializedAttrs),

    /**
     * Return the URL to use when syncing this model.
     *
     * Returns:
     *     string:
     *     The URL to use for syncing.
     */
    url() {
        return SITE_ROOT + this.get('localSitePrefix') +
               'api/validation/diffs/';
    },

    /**
     * Parse the result from the server.
     */
    parse() {
        // Do nothing
    }
});
