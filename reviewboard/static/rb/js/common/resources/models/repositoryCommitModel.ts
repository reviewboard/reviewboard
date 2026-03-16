/**
 * A commit in a repository.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    type DeserializerMap,
    type SerializerMap,
    BaseResource,
} from './baseResourceModel';


/**
 * Attributes for the RepositoryCommit model.
 *
 * Version Added:
 *     8.0
 */
export interface RepositoryCommitAttrs extends BaseResourceAttrs {
    /**
     * Whether this commit appears accessible.
     *
     * On some version control systems, not all commits may be accessible
     * due to ACLs or other policy mechanisms. In these cases, we shouldn't
     * let people try to make a review request for them, because it will fail.
     */
    accessible: boolean;

    /** The name of the author of the commit. */
    authorName: string;

    /** The date of the commit. */
    date: Date | string,

    /** The commit message or comment. */
    message: string;

    /** The ID of the commit's parent. */
    parent: string;

    /**
     * The URL of an existing review request for this commit, if one exists.
     */
    reviewRequestURL: string;

    /** The first line of the commit message. */
    summary: string;
}


/**
 * Resource data for the RepositoryCommit model.
 *
 * Version Added:
 *     8.0
 */
export interface RepositoryCommitResourceData
extends BaseResourceResourceData {
    author_name: string;
    date: string;
    message: string;
    parent: string;
    review_request_url: string;
    summary: string;
}


/**
 * A commit in a repository.
 */
@spina
export class RepositoryCommit extends BaseResource<
    RepositoryCommitAttrs,
    RepositoryCommitResourceData
> {
    static defaults: Result<Partial<RepositoryCommitAttrs>> = {
        accessible: true,
        authorName: null,
        date: null,
        message: null,
        parent: null,
        reviewRequestURL: null,
        summary: null,
    };

    static rspNamespace = 'commits';

    static deserializedAttrs = [
        'authorName',
        'date',
        'parent',
        'message',
        'summary',
        'reviewRequestURL',
    ];

    static serializedAttrs = [
        'authorName',
        'date',
        'id',
        'parent',
        'message',
        'reviewRequestURL',
    ];

    static attrToJsonMap: Record<string, string> = {
        authorName: 'author_name',
        reviewRequestURL: 'review_request_url',
        summary: 'message',
    };

    static deserializers: DeserializerMap = {
        date: (date: string) => {
            return date ? new Date(date) : '';
        },
        summary: (message: string) => message.split('\n', 1)[0],
    };

    static serializers: SerializerMap = {
        date: date => date.toString(),
    };

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *          The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(
        rsp: RepositoryCommitResourceData,
    ): Partial<RepositoryCommitAttrs> {
        const data = super.parseResourceData(rsp);

        data.accessible = !!(rsp.date || rsp.message || rsp.author_name);

        return data;
    }
}
