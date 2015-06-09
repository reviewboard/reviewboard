(function() {


var parentProto = RB.BaseResource.prototype;


/*
 * A diff to be uploaded to a server.
 *
 * For now, this is used only for uploading new diffs.
 *
 * It is expected that parentObject will be set to a ReviewRequest instance.
 */
RB.Diff = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            diff: null,
            parentDiff: null,
            basedir: null
        }, parentProto.defaults());
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
    ].concat(parentProto.serializedAttrs),

    payloadFileKeys: ['path', 'parent_diff_path'],

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
    }
});


})();
