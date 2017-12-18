/**
 * The base model for a comment.
 *
 * This provides all the common properties, serialization, deserialization,
 * validation, and other functionality of comments. It's meant to be
 * subclassed by more specific implementations.
 *
 * Model Attributes:
 *     forceTextType (string):
 *         The text format type to request for text in all responses.
 *
 *     includeTextTypes (string):
 *         A comma-separated list of text types to include in the payload when
 *         syncing the model.
 *
 *     issueOpened (boolean):
 *         Whether or not an issue is opened.
 *
 *     issueStatus (string):
 *         The current state of the issue. This must be one of
 *         ``STATE_DROPPED``, ``STATE_OPEN``, ``STATE_RESOLVED``,
 *         ``STATE_VERIFYING_DROPPED`` or ``STATE_VERIFYING_RESOLVED``.
 *
 *     markdownTextFields (object):
 *         The source contents of any Markdown text fields, if forceTextType is
 *         used and the caller fetches or posts with includeTextTypes=markdown.
 *         The keys in this object are the field names, and the values are the
 *         Markdown source of those fields.
 *
 *     rawTextFields (object):
 *         The contents of the raw text fields, if forceTextType is used and
 *         the caller fetches or posts with includeTextTypes=raw. The keys in this
 *         object are the field names, and the values are the raw versions of
 *         those attributes.
 *
 *     richText (boolean):
 *         Whether the comment is saved in rich-text (Markdown) format.
 *
 *     text (string):
 *         The text for the comment.
 */
RB.BaseComment = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            forceTextType: null,
            includeTextTypes: null,
            issueOpened: null,
            issueStatus: null,
            markdownTextFields: {},
            rawTextFields: {},
            richText: null,
            text: '',
        }, RB.BaseResource.prototype.defaults());
    },

    extraQueryArgs() {
        let textTypes = 'raw';

        if (RB.UserSession.instance.get('defaultUseRichText')) {
            textTypes += ',markdown';
        }

        return {
            'force-text-type': 'html',
            'include-text-types': textTypes
        };
    },

    supportsExtraData: true,

    attrToJsonMap: {
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        issueOpened: 'issue_opened',
        issueStatus: 'issue_status',
        richText: 'text_type'
    },

    serializedAttrs: [
        'forceTextType',
        'includeTextTypes',
        'issueOpened',
        'issueStatus',
        'richText',
        'text'
    ],

    deserializedAttrs: [
        'issueOpened',
        'issueStatus',
        'text',
        'html'
    ],

    serializers: {
        forceTextType: RB.JSONSerializers.onlyIfValue,
        includeTextTypes: RB.JSONSerializers.onlyIfValue,
        richText: RB.JSONSerializers.textType,
        issueStatus: function(value) {
            if (this.get('loaded')) {
                const parentObject = this.get('parentObject');

                if (parentObject.get('public')) {
                    return value;
                }
            }

            return undefined;
        }
    },

    /**
     * Destroy the comment if and only if the text is empty.
     *
     * This works just like destroy(), and will in fact call destroy()
     * with all provided arguments, but only if there's some actual
     * text in the comment.
     */
    destroyIfEmpty() {
        if (!this.get('text')) {
            this.destroy.apply(this, arguments);
        }
    },

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
    parseResourceData(rsp) {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.richText = (rawTextFields.text_type === 'markdown');

        if (rsp.raw_text_fields) {
            data.rawTextFields = {
                text: rsp.raw_text_fields.text
            };
        }

        if (rsp.markdown_text_fields) {
            data.markdownTextFields = {
                text: rsp.markdown_text_fields.text
            };
        }

        if (rsp.html_text_fields) {
            data.html = rsp.html_text_fields.text;
        }

        return data;
    },

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
    validate(attrs) {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return RB.BaseResource.strings.UNSET_PARENT_OBJECT;
        }

        if (attrs.issueStatus &&
            attrs.issueStatus !== RB.BaseComment.STATE_DROPPED &&
            attrs.issueStatus !== RB.BaseComment.STATE_OPEN &&
            attrs.issueStatus !== RB.BaseComment.STATE_RESOLVED &&
            attrs.issueStatus !== RB.BaseComment.STATE_VERIFYING_DROPPED &&
            attrs.issueStatus !== RB.BaseComment.STATE_VERIFYING_RESOLVED) {
            return RB.BaseComment.strings.INVALID_ISSUE_STATUS;
        }

        return RB.BaseResource.prototype.validate.apply(this, arguments);
    },

    /**
     * Return whether this comment issue requires verification before closing.
     *
     * Returns:
     *     boolean:
     *     True if the issue is marked to require verification.
     */
    requiresVerification() {
        const extraData = this.get('extraData');
        return extraData && extraData.require_verification === true;
    },

    /**
     * Return the username of the author of the comment.
     *
     * Returns:
     *     boolean:
     *     True if the current user is the author.
     */
    getAuthorUsername() {
        const review = this.get('parentObject');
        return review.get('links').user.title;
    },
}, {
    STATE_DROPPED: 'dropped',
    STATE_OPEN: 'open',
    STATE_RESOLVED: 'resolved',
    STATE_VERIFYING_DROPPED: 'verifying-dropped',
    STATE_VERIFYING_RESOLVED: 'verifying-resolved',

    /**
     * Return whether the given state should be considered open or closed.
     *
     * Args:
     *     state (string):
     *         The state to check.
     *
     * Returns:
     *     boolean:
     *     true if the given state is open.
     */
    isStateOpen(state) {
        return (state === RB.BaseComment.STATE_OPEN ||
                state === RB.BaseComment.STATE_VERIFYING_DROPPED ||
                state === RB.BaseComment.STATE_VERIFYING_RESOLVED);
    },

    strings: {
        INVALID_ISSUE_STATUS: 'issueStatus must be one of STATE_DROPPED, ' +
                              'STATE_OPEN, STATE_RESOLVED, ' +
                              'STATE_VERIFYING_DROPPED, or ' +
                              'STATE_VERIFYING_RESOLVED',
    },
});
