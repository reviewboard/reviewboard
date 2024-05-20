/**
 * Provides commenting functionality for diffs.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import * as JSONSerializers from '../utils/serializers';
import {
    type BaseCommentAttrs,
    type BaseCommentResourceData,
    BaseComment,
} from './baseCommentModel';
import {
    type SerializerMap,
} from './baseResourceModel';
import {
    type FileDiffResourceData,
    FileDiff,
} from './fileDiffModel';


/**
 * Attributes for the DiffComment model.
 *
 * Version Added:
 *     8.0
 */
export interface DiffCommentAttrs extends BaseCommentAttrs {
    /**
     * The ID of the base FileDiff in the cumulative diff for the comment.
     *
     * This attribute is mutually exclusive with ``interFileDiffID``.
     */
    baseFileDiffID: number | null;

    /** The first line number in the range (0-indexed). */
    beginLineNum: number;

    /** The last line number in the range (0-indexed). */
    endLineNum: number;

    /** The FileDiff that the comment applies to. */
    fileDiff: FileDiff | null;

    /** The ID of the FileDiff that the comment applies to. */
    fileDiffID: number | null;

    /**
     * The FileDiff at the end of an interdiff range for the comment.
     *
     * This attribute is mutually exclusive with ``baseFileDiffID``.
     */
    interFileDiff: FileDiff | null;

    /**
     * The ID of the FileDiff at the end of an interdiff range.
     *
     * This attribute is mutually exclusive with ``baseFileDiffID``.
     */
    interFileDiffID: number | null;
}


/**
 * Resource data for the DiffComment model.
 *
 * Version Added:
 *     8.0
 */
export interface DiffCommentResourceData extends BaseCommentResourceData {
    base_filediff_id: number;
    first_line: number;
    filediff: FileDiffResourceData;
    filediff_id: number;
    interfilediff: FileDiffResourceData;
    interfilediff_id: number;
    num_lines: number;
}


/**
 * Provides commenting functionality for diffs.
 *
 * A DiffComment represents a comment on a range of lines on either a
 * FileDiff or an interdiff consisting of two FileDiffs.
 */
@spina
export class DiffComment extends BaseComment<
    DiffCommentAttrs,
    DiffCommentResourceData
> {
    static defaults: Result<Partial<DiffCommentAttrs>> = {
        baseFileDiffID: null,
        beginLineNum: 0,
        endLineNum: 0,
        fileDiff: null,
        fileDiffID: null,
        interFileDiff: null,
        interFileDiffID: null,
    };

    static rspNamespace = 'diff_comment';
    static expandedFields = ['filediff', 'interfilediff'];

    static attrToJsonMap: Record<string, string> = {
        baseFileDiffID: 'base_filediff_id',
        beginLineNum: 'first_line',
        fileDiffID: 'filediff_id',
        interFileDiffID: 'interfilediff_id',
        numLines: 'num_lines',
    };

    static serializedAttrs = [
        'baseFileDiffID',
        'beginLineNum',
        'fileDiffID',
        'interFileDiffID',
        'numLines',
    ].concat(super.serializedAttrs);

    static deserializedAttrs = [
        'beginLineNum',
        'endLineNum',
    ].concat(super.deserializedAttrs);

    static serializers: SerializerMap = {
        baseFileDiffID: JSONSerializers.onlyIfUnloadedAndValue,
        fileDiffID: JSONSerializers.onlyIfUnloaded,
        interFileDiffID: JSONSerializers.onlyIfUnloadedAndValue,
        numLines: function() {
            return this.getNumLines();
        },
    };

    static strings = {
        BEGINLINENUM_GTE_0: 'beginLineNum must be >= 0',
        BEGINLINENUM_LTE_ENDLINENUM: 'beginLineNum must be <= endLineNum',
        ENDLINENUM_GTE_0: 'endLineNum must be >= 0',
        INVALID_FILEDIFF_ID: 'fileDiffID must be a valid ID',
    };

    /**
     * Return the total number of lines the comment spans.
     *
     * Returns:
     *     number:
     *     The total number of lines for the comment.
     */
    getNumLines(): number {
        return this.get('endLineNum') - this.get('beginLineNum') + 1;
    }

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
    parseResourceData(
        rsp: DiffCommentResourceData,
    ): Partial<DiffCommentAttrs> {
        const result = super.parseResourceData(rsp);

        result.endLineNum = rsp.num_lines + result.beginLineNum - 1;

        result.fileDiff = new FileDiff(rsp.filediff, {
            parse: true,
        });

        if (rsp.interfilediff) {
            result.interFileDiff = new FileDiff(rsp.interfilediff, {
                parse: true,
            });
        }

        return result;
    }

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
    validate(
        attrs: Partial<DiffCommentAttrs>,
    ): string {
        /*
         * XXX: Existing diff comments won't have the "fileDiffID" attribute
         * populated when we load the object from the API. Since we don't do
         * anything that needs that attribute unless we're trying to create a
         * new diff comment, only check it if isNew().
         */
        if (this.isNew() &&
            attrs.hasOwnProperty('fileDiffID') &&
            !attrs.fileDiffID) {
            return DiffComment.strings.INVALID_FILEDIFF_ID;
        }

        const hasBeginLineNum = attrs.hasOwnProperty('beginLineNum');

        if (hasBeginLineNum && attrs.beginLineNum < 0) {
            return DiffComment.strings.BEGINLINENUM_GTE_0;
        }

        const hasEndLineNum = attrs.hasOwnProperty('endLineNum');

        if (hasEndLineNum && attrs.endLineNum < 0) {
            return DiffComment.strings.ENDLINENUM_GTE_0;
        }

        if (hasBeginLineNum && hasEndLineNum &&
            attrs.beginLineNum > attrs.endLineNum) {
            return DiffComment.strings.BEGINLINENUM_LTE_ENDLINENUM;
        }

        return super.validate(attrs);
    }
}
