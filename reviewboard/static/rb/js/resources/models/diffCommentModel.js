(function() {


var parentProto = RB.BaseComment.prototype;


/*
 * Provides commenting functionality for diffs.
 *
 * A DiffComment represents a comment on a range of lines on either a
 * FileDiff or an interdiff consisting of two FileDiffs.
 */
RB.DiffComment = RB.BaseComment.extend({
    defaults: function() {
        return _.defaults({
            /* The first line number in the range (0-indexed). */
            beginLineNum: 0,

            /* The last line number in the range (0-indexed). */
            endLineNum: 0,

            /* The FileDiff the comment applies to. */
            fileDiff: null,

            /* The ID of the FileDiff the comment is on. */
            fileDiffID: null,

            /* The optional FileDiff at the end of an interdiff range. */
            interFileDiff: null,

            /*
             * The ID of the optional FileDiff specifying the end of an
             * interdiff range.
             */
            interFileDiffID: null
        }, parentProto.defaults());
    },

    rspNamespace: 'diff_comment',
    expandedFields: ['filediff', 'interfilediff'],

    attrToJsonMap: _.defaults({
        fileDiffID: 'filediff_id',
        beginLineNum: 'first_line',
        interFileDiffID: 'interfilediff_id',
        numLines: 'num_lines'
    }, parentProto.attrToJsonMap),

    serializedAttrs: [
        'beginLineNum',
        'numLines',
        'fileDiffID',
        'interFileDiffID'
    ].concat(parentProto.serializedAttrs),

    deserializedAttrs: [
        'beginLineNum',
        'endLineNum'
    ].concat(parentProto.deserializedAttrs),

    serializers: _.defaults({
        fileDiffID: RB.JSONSerializers.onlyIfUnloaded,
        interFileDiffID: RB.JSONSerializers.onlyIfUnloadedAndValue,

        numLines: function() {
            return this.getNumLines();
        }
    }, parentProto.serializers),

    /*
     * Returns the total number of lines the comment spans.
     */
    getNumLines: function() {
        return this.get('endLineNum') - this.get('beginLineNum') + 1;
    },

    /*
     * Deserializes comment data from an API payload.
     */
    parseResourceData: function(rsp) {
        var result = parentProto.parseResourceData.call(this, rsp);

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

    /*
     * Performs validation on the attributes of the model.
     *
     * This will check the range of line numbers to make sure they're
     * a valid ordered range, along with the default comment validation.
     */
    validate: function(attrs, options) {
        var strings = RB.DiffComment.strings,
            hasBeginLineNum,
            hasEndLineNum;

        /*
         * XXX: Existing diff comments won't have the "fileDiffID" attribute
         * populated when we load the object from the API. Since we don't do
         * anything that needs that attribute unless we're trying to create a
         * new diff comment, only check it if isNew().
         */
        if (this.isNew() && _.has(attrs, 'fileDiffID') && !attrs.fileDiffID) {
            return strings.INVALID_FILEDIFF_ID;
        }

        hasBeginLineNum = _.has(attrs, 'beginLineNum');

        if (hasBeginLineNum && attrs.beginLineNum < 0) {
            return strings.BEGINLINENUM_GTE_0;
        }

        hasEndLineNum = _.has(attrs, 'endLineNum');

        if (hasEndLineNum && attrs.endLineNum < 0) {
            return strings.ENDLINENUM_GTE_0;
        }

        if (hasBeginLineNum && hasEndLineNum &&
            attrs.beginLineNum > attrs.endLineNum) {
            return strings.BEGINLINENUM_LTE_ENDLINENUM;
        }

        return parentProto.validate.call(this, attrs, options);
    }
}, {
    strings: {
        INVALID_FILEDIFF_ID: 'fileDiffID must be a valid ID',
        BEGINLINENUM_GTE_0: 'beginLineNum must be >= 0',
        ENDLINENUM_GTE_0: 'endLineNum must be >= 0',
        BEGINLINENUM_LTE_ENDLINENUM: 'beginLineNum must be <= endLineNum'
    }
});


})();
