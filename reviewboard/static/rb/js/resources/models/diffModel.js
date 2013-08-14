/*
 * A diff to be uploaded to a server.
 *
 * For now, this is used only for uploading new diffs.
 *
 * It is expected that parentObject will be set to a ReviewRequest instance.
 */
RB.Diff = RB.BaseResource.extend({
    defaults: {
        diff: null,
        parentDiff: null,
        basedir: null
    },

    payloadFileKeys: ['path', 'parent_diff_path'],

    rspNamespace: 'diff',

    listKey: 'diffs',

    getErrorString: function(rsp) {
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
    },

    toJSON: function() {
        var payload;

        if (this.isNew()) {
            payload = {
                basedir: this.get('basedir'),
                path: this.get('diff'),
                parent_diff_path: this.get('parentDiff')
            };
        } else {
            payload = RB.BaseResource.prototype.toJSON.apply(this, arguments);
        }

        return payload;
    }
});
