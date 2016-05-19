/**
 * A diff to be uploaded to a server.
 *
 * For now, this is used only for uploading new diffs.
 *
 * It is expected that parentObject will be set to a ReviewRequest instance.
 */
RB.Diff = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            diff: null,
            parentDiff: null,
            basedir: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'diff',

    attrToJsonMap: {
        diff: 'path',
        parentDiff: 'parent_diff_path'
    },

    serializedAttrs: [
        'basedir',
        'diff',
        'parentDiff'
    ].concat(RB.BaseResource.prototype.serializedAttrs),

    payloadFileKeys: ['path', 'parent_diff_path'],

    listKey: 'diffs',

    /**
     * Return a user-facing error string for a given server response.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     string:
     *     A string to show to the user.
     */
    getErrorString(rsp) {
        if (rsp.err.code === RB.APIErrors.REPO_FILE_NOT_FOUND) {
            return interpolate(
                gettext('The file "%(file)s" (revision %(revision)s) was not found in the repository'),
                {
                    file: rsp.file,
                    revision: rsp.revision
                },
                true);
        }

        return rsp.err.msg;
    }
});
