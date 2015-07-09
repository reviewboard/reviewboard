/*
 * Review replies.
 *
 * Encapsulates replies to a top-level review.
 */
RB.ReviewReply = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /*
             * The text format type to request for text in all responses.
             */
            forceTextType: null,

            /*
             * Whether responses from the server should return raw text
             * fields when forceTextType is used.
             */
            includeTextTypes: null,

            /*
             * Raw text fields, if the caller fetches or posts with
             * include-text-types=raw.
             */
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

        'public': function(value) {
            return value ? true : undefined;
        }
    },

    COMMENT_LINK_NAMES: [
        'diff_comments',
        'file_attachment_comments',
        'screenshot_comments'
    ],

    parseResourceData: function(rsp) {
        var rawTextFields = rsp.raw_text_fields || rsp,
            data = RB.BaseResource.prototype.parseResourceData.call(this, rsp);

        data.bodyTopRichText =
            (rawTextFields.body_top_text_type === 'markdown');
        data.bodyBottomRichText =
            (rawTextFields.body_bottom_text_type === 'markdown');
        data.rawTextFields = rsp.raw_text_fields || {};

        return data;
    },

    /*
     * Publishes the reply.
     *
     * Before publishing, the "publishing" event will be triggered.
     * After successfully publishing, "published" will be triggered.
     */
    publish: function(options, context) {
        options = options || {};

        this.trigger('publishing');

        this.ready({
            ready: function() {
                this.set('public', true);
                this.save({
                    data: {
                        'public': 1,
                        trivial: options.trivial ? 1 : 0
                    },
                    success: function() {
                        this.trigger('published');

                        if (_.isFunction(options.success)) {
                            options.success.call(context);
                        }
                    },
                    error: function(model, xhr) {
                        model.trigger('publishError', xhr.errorText);

                        if (_.isFunction(options.error)) {
                            options.error.call(context, model, xhr);
                        }
                    }
                }, this);
            }
        }, this);
    },

    /*
     * Discards the reply if it's empty.
     *
     * If the reply doesn't have any remaining comments on the server, then
     * this will discard the reply.
     *
     * When we've finished checking, options.success will be called. It
     * will be passed true if discarded, or false otherwise.
     */
    discardIfEmpty: function(options, context) {
        options = _.bindCallbacks(options || {}, context);
        options.success = options.success || function() {};

        this.ready({
            ready: function() {
                if (this.isNew() ||
                    this.get('bodyTop') ||
                    this.get('bodyBottom')) {
                    options.success(false);
                    return;
                }

                this._checkCommentsLink(0, options, context);
            },

            error: options.error
        }, this);
    },

    /*
     * Checks if there are comments, given the comment type.
     *
     * This is part of the discardIfEmpty logic.
     *
     * If there are comments, we'll give up and call options.success(false).
     *
     * If there are no comments, we'll move on to the next comment type. If
     * we're done, the reply is discarded, and options.success(true) is called.
     */
    _checkCommentsLink: function(linkNameIndex, options, context) {
        var self = this,
            linkName = this.COMMENT_LINK_NAMES[linkNameIndex],
            url = this.get('links')[linkName].href;

        RB.apiCall({
            type: 'GET',
            url: url,
            success: function(rsp) {
                if (rsp[linkName].length > 0) {
                    if (options.success) {
                        options.success(false);
                    }
                } else if (linkNameIndex < self.COMMENT_LINK_NAMES.length - 1) {
                    self._checkCommentsLink(linkNameIndex + 1, options,
                                            context);
                } else {
                    self.destroy(
                    _.defaults({
                        success: function() {
                            options.success(true);
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
