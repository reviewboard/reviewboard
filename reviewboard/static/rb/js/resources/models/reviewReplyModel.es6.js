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
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async publish(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewReply.publish was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(options, context, newOptions =>
                this.publish(newOptions));
        }

        this.trigger('publishing');

        await this.ready();

        this.set('public', true);

        try {
            await this.save({
                data: {
                    'public': 1,
                    trivial: options.trivial ? 1 : 0
                },
            });
        } catch (err) {
            this.trigger('publishError', err.message);
            throw err;
        }

        this.trigger('published');
    },

    /**
     * Discard the reply if it's empty.
     *
     * If the reply doesn't have any remaining comments on the server, then
     * this will discard the reply.
     *
     * Version Changed:
     *     5.0:
     *     Changed to deprecate options and return a promise.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete. The
     *     resolution value will be true if discarded, false otherwise.
     */
    async discardIfEmpty(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewReply.discardIfEmpty was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(options, context, newOptions =>
                this.discardIfEmpty(newOptions));
        }

        await this.ready();

        if (this.isNew() || this.get('bodyTop') || this.get('bodyBottom')) {
            return false;
        } else {
            return this._checkCommentsLink(0);
        }
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
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete. The
     *     resolution value will be true if discarded, false otherwise.
     */
    _checkCommentsLink(linkNameIndex) {
        return new Promise((resolve, reject) => {
            const linkName = this.COMMENT_LINK_NAMES[linkNameIndex];
            const url = this.get('links')[linkName].href;

            RB.apiCall({
                type: 'GET',
                url: url,
                success: rsp => {
                    if (rsp[linkName].length > 0) {
                        resolve(false);
                    } else if (linkNameIndex < this.COMMENT_LINK_NAMES.length - 1) {
                        resolve(this._checkCommentsLink(linkNameIndex + 1));
                    } else {
                        resolve(this.destroy().then(() => true));
                    }
                },
                error: (model, xhr, options) => reject(
                    new BackboneError(model, xhr, options)),
            });
        });
    }
});
_.extend(RB.ReviewReply.prototype, RB.DraftResourceModelMixin);
