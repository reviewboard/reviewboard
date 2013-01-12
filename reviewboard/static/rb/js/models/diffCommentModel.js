/*
 * Provides commenting functionality for diffs.
 *
 * A DiffComment represents a comment on a range of lines on either a
 * FileDiff or an interdiff consisting of two FileDiffs.
 */
RB.DiffComment = RB.BaseComment.extend({
    defaults: _.defaults({
        /* The first line number in the range (0-indexed). */
        beginLineNum: 0,

        /* The last line number in the range (0-indexed). */
        endLineNum: 0,

        /* The ID of the FileDiff the comment is on. */
        fileDiffID: null,

        /*
         * The ID of the optional FileDiff specifying the end of an
         * interdiff range.
         */
        interFileDiffID: null
    }, RB.BaseComment.prototype.defaults),

    rspNamespace: 'diff_comment',

    /*
     * Returns the total number of lines the comment spans.
     */
    getNumLines: function() {
        return this.get('endLineNum') - this.get('beginLineNum') + 1;
    },

    /*
     * Serializes the comment to a payload that can be sent to the server.
     */
    toJSON: function() {
        var data = _.defaults({
            first_line: this.get('beginLineNum'),
            num_lines: this.getNumLines()
        }, RB.BaseComment.prototype.toJSON.call(this));

        if (!this.get('loaded')) {
            var fileDiffID = this.get('fileDiffID'),
                interFileDiffID = this.get('interFileDiffID');

            data.filediff_id = fileDiffID

            if (interFileDiffID) {
                data.interfilediff_id = interFileDiffID;
            }
        }

        return data;
    },

    /*
     * Deserializes comment data from an API payload.
     */
    parse: function(rsp) {
        var result = RB.BaseComment.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.beginLineNum = rspData.first_line;
        result.endLineNum = rspData.num_lines + result.beginLineNum - 1;

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

        if (_.has(attrs, 'fileDiffID') && !attrs.fileDiffID) {
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

        return RB.BaseComment.prototype.validate.call(this, attrs, options);
    }
}, {
    strings: {
        INVALID_FILEDIFF_ID: 'fileDiffID must be a valid ID',
        BEGINLINENUM_GTE_0: 'beginLineNum must be >= 0',
        ENDLINENUM_GTE_0: 'endLineNum must be >= 0',
        BEGINLINENUM_LTE_ENDLINENUM: 'beginLineNum must be <= endLineNum'
    }
});
