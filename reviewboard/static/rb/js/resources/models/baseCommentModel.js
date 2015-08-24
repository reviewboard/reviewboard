/*
 * The base model for a comment.
 *
 * This provides all the common properties, serialization, deserialization,
 * validation, and other functionality of comments. It's meant to be
 * subclassed by more specific implementations.
 */
RB.BaseComment = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /*
             * The text format type to request for text in all responses.
             */
            forceTextType: null,

            /*
             * A string containing a comma-separated list of text types to
             * include in the payload.
             */
            includeTextTypes: null,

            /* Whether or not an issue is opened. */
            issueOpened: null,

            /*
             * The current state of the issue.
             *
             * This must be one of STATE_DROPPED, STATE_OPEN, or
             * STATE_RESOLVED.
             */
            issueStatus: null,

            /*
             * Raw text fields, if the caller fetches or posts with
             * include-text-types=raw.
             */
            rawTextFields: {},

            /* Whether the comment is saved in rich-text (Markdown) format. */
            richText: null,

            /* The text entered for the comment. */
            text: ''
        }, RB.BaseResource.prototype.defaults());
    },

    extraQueryArgs: function() {
        var textTypes = 'raw';

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
        'text'
    ],

    serializers: {
        forceTextType: RB.JSONSerializers.onlyIfValue,
        includeTextTypes: RB.JSONSerializers.onlyIfValue,
        richText: RB.JSONSerializers.textType,

        issueStatus: function(value) {
            var parentObject;

            if (this.get('loaded')) {
                parentObject = this.get('parentObject');

                if (parentObject.get('public')) {
                    return value;
                }
            }

            return undefined;
        }
    },

    /*
     * Destroys the comment if and only if the text is empty.
     *
     * This works just like destroy(), and will in fact call destroy()
     * with all provided arguments, but only if there's some actual
     * text in the comment.
     */
    destroyIfEmpty: function(options, context) {
        if (!this.get('text')) {
            this.destroy(options, context);
        }
    },

    /*
     * Deserializes comment data from an API payload.
     *
     * This must be overloaded by subclasses, and the parent version called.
     */
    parseResourceData: function(rsp) {
        var rawTextFields = rsp.raw_text_fields || rsp,
            data = RB.BaseResource.prototype.parseResourceData.call(this, rsp);

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

        return data;
    },

    /*
     * Performs validation on the attributes of the model.
     *
     * By default, this validates the issueStatus field. It can be
     * overridden to provide additional validation, but the parent
     * function must be called.
     */
    validate: function(attrs) {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return RB.BaseResource.strings.UNSET_PARENT_OBJECT;
        }

        if (attrs.issueStatus &&
            attrs.issueStatus !== RB.BaseComment.STATE_DROPPED &&
            attrs.issueStatus !== RB.BaseComment.STATE_OPEN &&
            attrs.issueStatus !== RB.BaseComment.STATE_RESOLVED) {
            return RB.BaseComment.strings.INVALID_ISSUE_STATUS;
        }

        return RB.BaseResource.prototype.validate.apply(this, arguments);
    }
}, {
    STATE_DROPPED: 'dropped',
    STATE_OPEN: 'open',
    STATE_RESOLVED: 'resolved',

    strings: {
        INVALID_ISSUE_STATUS: 'issueStatus must be one of STATE_DROPPED, ' +
                              'STATE_OPEN, or STATE_RESOLVED'
    }
});
