/**
 * The base model for a comment.
 */

import { spina } from '@beanbag/spina';

import { UserSession } from '../../models/userSessionModel';
import * as JSONSerializers from '../utils/serializers';
import {
    type BaseResourceAttrs,
    BaseResource,
} from './baseResourceModel';


/**
 * A valid issue status type.
 *
 * Version Added:
 *     7.0
 */
export enum CommentIssueStatusType {
    DROPPED = 'dropped',
    OPEN = 'open',
    RESOLVED = 'resolved',
    VERIFYING_DROPPED = 'verifying-dropped',
    VERIFYING_RESOLVED = 'verifying-resolved',
}


/**
 * Attributes for the BaseComment model.
 *
 * Version Added:
 *     7.0
 */
export interface BaseCommentAttrs extends BaseResourceAttrs {
    /** The text format type to request for text in all responses. */
    forceTextType: string;

    /** The HTML representation of the comment text. */
    html: string;

    /**
     * A comma-separated list of text types to include in the payload when
     * syncing the model.
     */
    includeTextTypes: string;

    /** Whether or not an issue is opened. */
    issueOpened: boolean;

    /**
     * The current state of the issue. This must be one of:
     *
     * * ``dropped``
     * * ``open``
     * * ``resolved``
     * * ``verifying-dropped``
     * * ``verifying-resolved``
     */
    issueStatus: CommentIssueStatusType;

    /**
     * The source contents of any Markdown text fields, if forceTextType is
     * used and the caller fetches or posts with includeTextTypes=markdown. The
     * keys in this object are the field names, and the values are the Markdown
     * source of those fields.
     */
    markdownTextFields: { [key: string]: string };

    /**
     * The contents of the raw text fields, if forceTextType is used and the
     * caller fetches or posts with includeTextTypes=raw. The keys in this
     * object are the field names, and the values are the raw versions of those
     * attributes.
     */
    rawTextFields: { [key: string]: string };

    /** Whether the comment is saved in rich-text (Markdown) format. */
    richText: boolean;

    /** The text for the comment. */
    text: string;
}


/**
 * Base comment resource data returned by the server.
 *
 * Version Added:
 *     7.0
 */
export interface BaseCommentResourceData {
    force_text_type: string;
    html: string;
    html_text_fields: { [key: string]: string };
    include_text_types: string;
    issue_opened: boolean;
    issue_status: string;
    markdown_text_fields: { [key: string]: string };
    raw_text_fields: { [key: string]: string };
    rich_text: boolean;
    text: string;
    timestamp: string;
}


/**
 * The base model for a comment.
 *
 * This provides all the common properties, serialization, deserialization,
 * validation, and other functionality of comments. It's meant to be
 * subclassed by more specific implementations.
 */
@spina
export class BaseComment<
    TAttributes extends BaseCommentAttrs = BaseCommentAttrs
> extends BaseResource<TAttributes> {
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     BaseCommentAttrs:
     *     The default values for the model attributes.
     */
    static defaults(): BaseCommentAttrs {
        return _.defaults({
            forceTextType: null,
            html: null,
            includeTextTypes: null,
            issueOpened: null,
            issueStatus: null,
            markdownTextFields: {},
            rawTextFields: {},
            richText: null,
            text: '',
        }, super.defaults());
    }

    /**
     * Return extra arguments to add to API query strings.
     *
     * Returns:
     *     object:
     *     Any extra query arguments for GET requests.
     */
    static extraQueryArgs(): { [key: string]: string } {
        let textTypes = 'raw';

        if (UserSession.instance.get('defaultUseRichText')) {
            textTypes += ',markdown';
        }

        return {
            'force-text-type': 'html',
            'include-text-types': textTypes,
        };
    }

    static supportsExtraData = true;

    static attrToJsonMap = {
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        issueOpened: 'issue_opened',
        issueStatus: 'issue_status',
        richText: 'text_type',
    };

    static serializedAttrs = [
        'forceTextType',
        'includeTextTypes',
        'issueOpened',
        'issueStatus',
        'richText',
        'text',
    ];

    static deserializedAttrs = [
        'issueOpened',
        'issueStatus',
        'text',
        'html',
    ];

    static serializers = {
        forceTextType: JSONSerializers.onlyIfValue,
        includeTextTypes: JSONSerializers.onlyIfValue,
        issueStatus: function(value) {
            if (this.get('loaded')) {
                const parentObject = this.get('parentObject');

                if (parentObject.get('public')) {
                    return value;
                }
            }

            return undefined;
        },
        richText: JSONSerializers.textType,
    };

    /*
     * Legacy definitions for an issue status type.
     *
     * These remain around for compatibility reasons, but are pending
     * deprecation.
     */
    static STATE_DROPPED = CommentIssueStatusType.DROPPED;
    static STATE_OPEN = CommentIssueStatusType.OPEN;
    static STATE_RESOLVED = CommentIssueStatusType.RESOLVED;
    static STATE_VERIFYING_DROPPED = CommentIssueStatusType.VERIFYING_DROPPED;
    static STATE_VERIFYING_RESOLVED =
        CommentIssueStatusType.VERIFYING_RESOLVED;

    static strings: { [key: string]: string } = {
        INVALID_ISSUE_STATUS: dedent`
            issueStatus must be one of STATE_DROPPED, STATE_OPEN,
            STATE_RESOLVED, STATE_VERIFYING_DROPPED, or
            STATE_VERIFYING_RESOLVED.
        `,
    };

    /**
     * Return whether the given state should be considered open or closed.
     *
     * Args:
     *     state (string):
     *         The state to check.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the given state is open.
     */
    static isStateOpen(
        state: CommentIssueStatusType,
    ): boolean {
        return (state === CommentIssueStatusType.OPEN ||
                state === CommentIssueStatusType.VERIFYING_DROPPED ||
                state === CommentIssueStatusType.VERIFYING_RESOLVED);
    }

    /**
     * Destroy the comment if and only if the text is empty.
     *
     * This works just like destroy(), and will in fact call destroy()
     * with all provided arguments, but only if there's some actual
     * text in the comment.
     */
    destroyIfEmpty() {
        if (!this.get('text')) {
            this.destroy();
        }
    }

    /**
     * Deserialize comment data from an API payload.
     *
     * This must be overloaded by subclasses, and the parent version called.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(
        rsp: BaseCommentResourceData,
    ): Partial<TAttributes> {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = super.parseResourceData(rsp);

        data.richText = (rawTextFields['text_type'] === 'markdown');

        if (rsp.raw_text_fields) {
            data.rawTextFields = {
                text: rsp.raw_text_fields.text,
            };
        }

        if (rsp.markdown_text_fields) {
            data.markdownTextFields = {
                text: rsp.markdown_text_fields.text,
            };
        }

        if (rsp.html_text_fields) {
            data.html = rsp.html_text_fields.text;
        }

        return data;
    }

    /**
     * Perform validation on the attributes of the model.
     *
     * By default, this validates the issueStatus field. It can be
     * overridden to provide additional validation, but the parent
     * function must be called.
     *
     * Args:
     *     attrs (object):
     *         Attribute values to validate.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(
        attrs: TAttributes,
    ): string {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return BaseResource.strings.UNSET_PARENT_OBJECT;
        }

        const issueStatus = attrs.issueStatus;

        if (issueStatus &&
            issueStatus !== CommentIssueStatusType.DROPPED &&
            issueStatus !== CommentIssueStatusType.OPEN &&
            issueStatus !== CommentIssueStatusType.RESOLVED &&
            issueStatus !== CommentIssueStatusType.VERIFYING_DROPPED &&
            issueStatus !== CommentIssueStatusType.VERIFYING_RESOLVED) {
            return BaseComment.strings.INVALID_ISSUE_STATUS;
        }

        return super.validate(attrs);
    }

    /**
     * Return whether this comment issue requires verification before closing.
     *
     * Returns:
     *     boolean:
     *     True if the issue is marked to require verification.
     */
    requiresVerification(): boolean {
        const extraData = this.get('extraData');

        return extraData && extraData.require_verification === true;
    }

    /**
     * Return the username of the author of the comment.
     *
     * Returns:
     *     string:
     *     The username of the comment's author.
     */
    getAuthorUsername(): string {
        const review = this.get('parentObject');

        return review.get('links').user.title;
    }
}
