/**
 * A model for giving the user hints about comments in other revisions.
 */

import { BaseModel, ModelAttributes, spina } from '@beanbag/spina';


/**
 * Attributes for the DiffCommentsHint model.
 *
 * Version Added:
 *     7.0
 */
export interface DiffCommentsHintAttrs extends ModelAttributes {
    /** Whether there are any comments on other revisions. */
    hasOtherComments: boolean;

    /** An array of diffset revisions with comments. */
    diffsetsWithComments: {
        isCurrent: boolean;
        revision: number;
    }[];

    /** An array of interdiffs with comments. */
    interdiffsWithComments: {
        isCurrent: boolean;
        oldRevision: number;
        newRevision: number;
    }[];

    /** An array of commit ranges with comments. */
    commitsWithComments: {
        isCurrent: boolean;
        revision: number;
        baseCommitID: string | null;
        baseCommitPK: number | null;
        tipCommitID: string | null;
        tipCommitPK: number | null;
    }[];
}


/**
 * Resource data returned by the server.
 *
 * Version Added:
 *     7.0
 */
export interface DiffCommentsHintParseData {
    has_other_comments: boolean;

    diffsets_with_comments: {
        is_current: boolean;
        revision: number;
    }[];

    interdiffs_with_comments: {
        is_current: boolean;
        old_revision: number;
        new_revision: number;
    }[];

    commits_with_comments: {
        base_commit_id: string | null;
        base_commit_pk: number | null;
        is_current: boolean;
        revision: number;
        tip_commit_id: string | null;
        tip_commit_pk: number | null;
    }[];
}


/**
 * A model for giving the user hints about comments in other revisions.
 *
 * Version Changed:
 *     7.0:
 *     Added the commitsWithComments attribute.
 */
@spina
export class DiffCommentsHint extends BaseModel<DiffCommentsHintAttrs> {
    /**
     * Return the defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The defaults for the model.
     */
    static defaults(): DiffCommentsHintAttrs {
        return {
            commitsWithComments: [],
            diffsetsWithComments: [],
            hasOtherComments: false,
            interdiffsWithComments: [],
        };
    }

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The data received from the server.
     *
     * Returns:
     *     object:
     *     The parsed result.
     */
    parse(
        rsp: DiffCommentsHintParseData,
    ): Partial<DiffCommentsHintAttrs> {
        return {
            commitsWithComments: rsp.commits_with_comments.map(
                commit => ({
                    baseCommitID: commit.base_commit_id,
                    baseCommitPK: commit.base_commit_pk,
                    isCurrent: commit.is_current,
                    revision: commit.revision,
                    tipCommitID: commit.tip_commit_id,
                    tipCommitPK: commit.tip_commit_pk,
                })),
            diffsetsWithComments: rsp.diffsets_with_comments.map(
                diffset => ({
                    isCurrent: diffset.is_current,
                    revision: diffset.revision,
                })),
            hasOtherComments: rsp.has_other_comments,
            interdiffsWithComments: rsp.interdiffs_with_comments.map(
                interdiff => ({
                    isCurrent: interdiff.is_current,
                    newRevision: interdiff.new_revision,
                    oldRevision: interdiff.old_revision,
                })),
        };
    }
}
