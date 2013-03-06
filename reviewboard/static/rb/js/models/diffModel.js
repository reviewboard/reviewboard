/*
 * A diff to be uploaded to a server.
 *
 * For now, this is used only for uploading new diffs.
 *
 * It is expected that parentObject will be set to a ReviewRequest instance.
 */
RB.Diff = RB.BaseResource.extend({
    rspNamespace: 'diff',

    getErrorString: function(rsp) {
        if (rsp.err.code == 207) {
            return 'The file "' + rsp.file + '" (revision ' + rsp.revision +
                    ') was not found in the repository';
        }

        return rsp.err.msg;
    }
});
