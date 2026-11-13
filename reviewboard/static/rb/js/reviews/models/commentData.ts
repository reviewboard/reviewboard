/**
 * Structures for serialized comment data.
 *
 * Version Added:
 *     7.0
 */


/**
 * Serialized data for a comment.
 *
 * This must be kept in sync with the definitions in
 * :file:`reviewboard/reviews/ui/base.py`.
 *
 * Version Added:
 *     7.0
 */
export interface SerializedComment {
    /** The ID of the comment. */
    comment_id: number;

    /** The rendered HTML version of the comment text. */
    html: string;

    /** Whether the comment opens an issue. */
    issue_opened: boolean;

    /** The status of the issue, if one was opened. */
    issue_status: string;

    /** Whether the comment is part of the user's current draft review. */
    localdraft: boolean;

    /** The ID of the review that this comment is a part of. */
    review_id: number,

    /** The ID of the review request that this comment is on. */
    review_request_id: number;

    /** Whether the comment text should be rendered in Markdown. */
    rich_text: boolean;

    /** The raw text of the comment. */
    text: string;

    /** The URL to link to for the comment. */
    url: string;

    /** Information about the author of the comment. */
    user: {
        /** The user's full name, if available. */
        name: string;

        /** The user's username. */
        username: string;
    };
}


/**
 * Serialized data on which view of a file a comment was made on.
 *
 * This is used for files that can be shown as source or rendered, such as
 * Markdown.
 *
 * This must be kept in sync with the definitions in
 * :file:`reviewboard/reviews/ui/base.py`.
 *
 * Version Added:
 *     9.0
 */
export interface SerializedViewModeData {
    /**
     * The view of the file when the comment was made.
     *
     * This will be either "source" or "rendered".
     */
    viewMode: string;

    /** The version of the row layout used for the rendered view. */
    renderVersion?: number;
}


/**
 * The comment block fields holding view mode data.
 *
 * Version Added:
 *     9.0
 */
export const VIEW_MODE_COMMENT_FIELDS = ['renderVersion', 'viewMode'];


/**
 * Return the view mode data from serialized comment fields.
 *
 * Version Added:
 *     9.0
 *
 * Args:
 *     fields (SerializedViewModeData):
 *         The serialized comment fields.
 *
 * Returns:
 *     SerializedViewModeData:
 *     The view mode data. Missing fields are left out, so the comment
 *     block's defaults apply.
 */
export function parseViewModeData(
    fields: Partial<SerializedViewModeData>,
): Partial<SerializedViewModeData> {
    const data: Partial<SerializedViewModeData> = {};

    if (fields.viewMode !== undefined) {
        data.viewMode = fields.viewMode;
    }

    if (fields.renderVersion !== undefined) {
        data.renderVersion = fields.renderVersion;
    }

    return data;
}


/**
 * Serialized data for a diff comment.
 *
 * This must be kept in sync with the definitions in
 * :file:`reviewboard/reviews/ui/diff.py`.
 *
 * Version Added:
 *     7.0
 */
export interface SerializedDiffComment extends SerializedComment {
    /** The line that the comment starts on. */
    line: number;

    /** The number of lines that the comment spans. */
    num_lines: number;
}


/**
 * Serialized data for a region comment.
 *
 * This must be kept in sync with the definitions in
 * :file:`reviewboard/reviews/ui/image.py`.
 *
 * Version Added:
 *     7.0
 */
export interface SerializedRegionComment extends SerializedComment {
    /** The X position of the comment block, in pixels. */
    x: number;

    /** The Y position of the comment block, in pixels. */
    y: number;

    /** The width of the comment block, in pixels. */
    width: number;

    /** The height of the comment block, in pixels. */
    height: number;
}


/**
 * Serialized data for a text comment.
 *
 * This must be kept in sync with the definitions in
 * :file:`reviewboard/reviews/ui/text.py`.
 *
 * Version Added:
 *     7.0
 */
export interface SerializedTextComment
    extends SerializedComment, SerializedViewModeData {
    /** The starting line number of the comment. */
    beginLineNum: number;

    /** The ending line number of the comment. */
    endLineNum: number;
}
