/**
 * A review reply.
 *
 * Encapsulates replies to a top-level review.
 *
 * Model Attributes:
 *     forceTextType (string):
 *         The text type to request for text in all responses.
 *
 *     includeTextTypes (string):
 *         A comma-separated list of text types to include in responses.
 *
 *     rawTextFields (object):
 *         The contents of the raw text fields, if forceTextType is used and
 *         the caller fetches or posts with includeTextTypes=raw. The keys in
 *         this object are the field names, and the values are the raw versions
 *         of those attributes.
 *
 *     review (RB.Review):
 *         The review that this reply is replying to.
 *
 *     public (boolean):
 *         Whether this reply has been published.
 *
 *     bodyTop (string):
 *         The reply to the original review's ``bodyTop``.
 *
 *     bodyTopRichText (boolean):
 *         Whether the ``bodyTop`` field should be rendered as Markdown.
 *
 *     bodyBottom (string):
 *         The reply to the original review's ``bodyBottom``.
 *
 *     bodyBottomRichText (boolean):
 *         Whether the ``bodyBottom`` field should be rendered as Markdown.
 *
 *     timestamp (string):
 *         The timestamp of this reply.
 */
RB.ReviewReply = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            forceTextType: null,
            includeTextTypes: null,
            rawTextFields: {},
            review: null,
            'public': false,
            bodyTop: null,
            bodyTopRichText: false,
            bodyBottom: null,
            bodyBottomRichText: false,
            timestamp: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'reply',
    listKey: 'replies',

    extraQueryArgs: {
        'force-text-type': 'html',
        'include-text-types': 'raw'
    },

    attrToJsonMap: {
        bodyBottom: 'body_bottom',
        bodyBottomRichText: 'body_bottom_text_type',
        bodyTop: 'body_top',
        bodyTopRichText: 'body_top_text_type',
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types'
    },

    serializedAttrs: [
        'forceTextType',
        'includeTextTypes',
        'bodyTop',
        'bodyTopRichText',
        'bodyBottom',
        'bodyBottomRichText',
        'public'
    ],

    deserializedAttrs: [
        'bodyTop',
        'bodyBottom',
        'public',
        'timestamp'
    ],

    serializers: {
        forceTextType: RB.JSONSerializers.onlyIfValue,
        includeTextTypes: RB.JSONSerializers.onlyIfValue,
        bodyTopRichText: RB.JSONSerializers.textType,
        bodyBottomRichText: RB.JSONSerializers.textType,
        'public': value => value ? true : undefined
    },

    COMMENT_LINK_NAMES: [
        'diff_comments',
        'file_attachment_comments',
        'general_comments',
        'screenshot_comments'
    ],

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     The attribute values to set on the model.
     */
    parseResourceData(rsp) {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.bodyTopRichText =
            (rawTextFields.body_top_text_type === 'markdown');
        data.bodyBottomRichText =
            (rawTextFields.body_bottom_text_type === 'markdown');
        data.rawTextFields = rsp.raw_text_fields || {};

        return data;
    },

    /**
     * Publish the reply.
     *
     * Before publishing, the "publishing" event will be triggered.
     * After successfully publishing, "published" will be triggered.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    publish(options={}, context=undefined) {
        this.trigger('publishing');

        this.ready({
            ready: () => {
                this.set('public', true);
                this.save({
                    data: {
                        'public': 1,
                        trivial: options.trivial ? 1 : 0
                    },
                    success: () => {
                        this.trigger('published');

                        if (_.isFunction(options.success)) {
                            options.success.call(context);
                        }
                    },
                    error: (model, xhr) => {
                        model.trigger('publishError', xhr.errorText);

                        if (_.isFunction(options.error)) {
                            options.error.call(context, model, xhr);
                        }
                    }
                });
            }
        });
    },

    /**
     * Discard the reply if it's empty.
     *
     * If the reply doesn't have any remaining comments on the server, then
     * this will discard the reply.
     *
     * When we've finished checking, options.success will be called. It
     * will be passed true if discarded, or false otherwise.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    discardIfEmpty(options={}, context=undefined) {
        options = _.bindCallbacks(options, context);

        this.ready({
            ready: () => {
                if (this.isNew() ||
                    this.get('bodyTop') ||
                    this.get('bodyBottom')) {
                    if (_.isFunction(options.success)) {
                        options.success(false);
                    }

                    return;
                }

                this._checkCommentsLink(0, options, context);
            },

            error: options.error
        });
    },

    /**
     * Check if there are comments, given the comment type.
     *
     * This is part of the discardIfEmpty logic.
     *
     * If there are comments, we'll give up and call options.success(false).
     *
     * If there are no comments, we'll move on to the next comment type. If
     * we're done, the reply is discarded, and options.success(true) is called.
     *
     * Args:
     *     linkNamesIndex (number):
     *         An index into the ``COMMENT_LINK_NAMES`` Array.
     *
     *     options (object):
     *         Options for the save operation.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    _checkCommentsLink(linkNameIndex, options, context) {
        const linkName = this.COMMENT_LINK_NAMES[linkNameIndex];
        const url = this.get('links')[linkName].href;

        RB.apiCall({
            type: 'GET',
            url: url,
            success: rsp => {
                if (rsp[linkName].length > 0) {
                    if (_.isFunction(options.success)) {
                        options.success(false);
                    }
                } else if (linkNameIndex < this.COMMENT_LINK_NAMES.length - 1) {
                    this._checkCommentsLink(linkNameIndex + 1, options,
                                            context);
                } else {
                    this.destroy(
                    _.defaults({
                        success: () => {
                            if (_.isFunction(options.success)) {
                                options.success(true);
                            }
                        }
                    }, options),
                    context);
                }
            },
            error: options.error
        });
    }
});
_.extend(RB.ReviewReply.prototype, RB.DraftResourceModelMixin);
