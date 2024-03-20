/**
 * Structures for serialized comment data.
 *
 * Version Added:
 *     7.0
 */


/**
 * Serialized data for a comment block.
 *
 * Version Added:
 *     7.0
 */
export interface SerializedComment {
    comment_id: number;
    html: string;
    issue_opened: boolean;
    issue_status: string;
    localdraft: boolean;
    review_id: number,
    rich_text: boolean;
    text: string;
    user: {
        name: string;
        username: string;
    };
}
