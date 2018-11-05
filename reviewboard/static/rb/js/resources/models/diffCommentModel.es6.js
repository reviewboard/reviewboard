/**
 * Provides commenting functionality for diffs.
 *
 * A DiffComment represents a comment on a range of lines on either a
 * FileDiff or an interdiff consisting of two FileDiffs.
 *
 * Model Attributes:
 *     beginLineNum (number):
 *         The first line number in the range (0-indexed).
 *
 *     endLineNum (number):
 *         The last line number in the range (0-indexed).
 *
 *     fileDiff (RB.FileDiff):
 *         The FileDiff that the comment applies to.
 *
 *     fileDiffID (number):
 *         The ID of the FileDiff that the comment applies to.
 *
 *     interFileDiff (RB.FileDiff):
 *         The FileDiff at the end of an interdiff range that the comment
 *         applies to, if appropriate.
 *
 *         This attribute is mutually exclusive with ``baseFileDiffID``.
 *
 *     interFileDiffID (number):
 *         The ID of the FileDiff at the end of an interdiff range that the
 *         comment applies to.
 *
 *         This attribute is mutually exclusive with ``baseFileDiffID``.
 *
 *     baseFileDiffID (number):
 *         The ID of the base FileDiff in the cumulative diff that the
 *         comment is on.
 *
 *         This attribute is mutually exclusive with ``interFileDiffID``.
 */
RB.DiffComment = RB.BaseComment.extend({
    defaults: _.defaults({
        beginLineNum: 0,
        endLineNum: 0,
        fileDiff: null,
        fileDiffID: null,
        interFileDiff: null,
        interFileDiffID: null,
        baseFileDiffID: null,
    }, RB.BaseComment.prototype.defaults()),

    rspNamespace: 'diff_comment',
    expandedFields: ['filediff', 'interfilediff'],

    attrToJsonMap: _.defaults({
        baseFileDiffID: 'base_filediff_id',
        beginLineNum: 'first_line',
        fileDiffID: 'filediff_id',
        interFileDiffID: 'interfilediff_id',
        numLines: 'num_lines',
    }, RB.BaseComment.prototype.attrToJsonMap),

    serializedAttrs: [
        'baseFileDiffID',
        'beginLineNum',
        'fileDiffID',
        'interFileDiffID',
        'numLines',
    ].concat(RB.BaseComment.prototype.serializedAttrs),

    deserializedAttrs: [
        'beginLineNum',
        'endLineNum'
    ].concat(RB.BaseComment.prototype.deserializedAttrs),

    serializers: _.defaults({
        fileDiffID: RB.JSONSerializers.onlyIfUnloaded,
        interFileDiffID: RB.JSONSerializers.onlyIfUnloadedAndValue,
        baseFileDiffID: RB.JSONSerializers.onlyIfUnloadedAndValue,
        numLines: function() {
            return this.getNumLines();
        }
    }, RB.BaseComment.prototype.serializers),

    /**
     * Return the total number of lines the comment spans.
     *
     * Returns:
     *     number:
     *     The total number of lines for the comment.
     */
    getNumLines() {
        return this.get('endLineNum') - this.get('beginLineNum') + 1;
    },

    /**
     * Deserialize comment data from an API payload.
     *
     * Args:
     *     rsp (object):
     *         The data from the server.
     *
     * Returns:
     *     object:
     *     The model attributes to assign.
     */
    parseResourceData(rsp) {
        const result = RB.BaseComment.prototype.parseResourceData.call(
            this, rsp);

        result.endLineNum = rsp.num_lines + result.beginLineNum - 1;

        result.fileDiff = new RB.FileDiff(rsp.filediff, {
            parse: true
        });

        if (rsp.interfilediff) {
            result.interFileDiff = new RB.FileDiff(rsp.interfilediff, {
                parse: true
            });
        }
        return result;
    },

    /**
     * Perform validation on the attributes of the model.
     *
     * This will check the range of line numbers to make sure they're
     * a valid ordered range, along with the default comment validation.
     *
     * Args:
     *     attrs (object):
     *         The set of attributes to validate.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(attrs) {
        /*
         * XXX: Existing diff comments won't have the "fileDiffID" attribute
         * populated when we load the object from the API. Since we don't do
         * anything that needs that attribute unless we're trying to create a
         * new diff comment, only check it if isNew().
         */
        if (this.isNew() && _.has(attrs, 'fileDiffID') && !attrs.fileDiffID) {
            return RB.DiffComment.strings.INVALID_FILEDIFF_ID;
        }

        const hasBeginLineNum = _.has(attrs, 'beginLineNum');

        if (hasBeginLineNum && attrs.beginLineNum < 0) {
            return RB.DiffComment.strings.BEGINLINENUM_GTE_0;
        }

        const hasEndLineNum = _.has(attrs, 'endLineNum');

        if (hasEndLineNum && attrs.endLineNum < 0) {
            return RB.DiffComment.strings.ENDLINENUM_GTE_0;
        }

        if (hasBeginLineNum && hasEndLineNum &&
            attrs.beginLineNum > attrs.endLineNum) {
            return RB.DiffComment.strings.BEGINLINENUM_LTE_ENDLINENUM;
        }

        return RB.BaseComment.prototype.validate.apply(this, arguments);
    }
}, {
    strings: {
        INVALID_FILEDIFF_ID: 'fileDiffID must be a valid ID',
        BEGINLINENUM_GTE_0: 'beginLineNum must be >= 0',
        ENDLINENUM_GTE_0: 'endLineNum must be >= 0',
        BEGINLINENUM_LTE_ENDLINENUM: 'beginLineNum must be <= endLineNum'
    }
});
