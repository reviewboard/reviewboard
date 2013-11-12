/*
 * Review replies.
 *
 * Encapsulates replies to a top-level review.
 */
RB.ReviewReply = RB.BaseResource.extend({
    defaults: _.defaults({
        review: null,
        public: false,
        richText: false,
        bodyTop: null,
        bodyBottom: null,
        timestamp: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'reply',
    listKey: 'replies',

    COMMENT_LINK_NAMES: [
        'diff_comments',
        'file_attachment_comments',
        'screenshot_comments'
    ],

    toJSON: function() {
        return {
            'public': this.get('public'),
            'body_top': this.get('bodyTop'),
            'body_bottom': this.get('bodyBottom'),
            'rich_text': this.get('richText')
        };
    },

    parseResourceData: function(rsp) {
        return {
            bodyTop: rsp.body_top,
            bodyBottom: rsp.body_bottom,
            public: rsp.public,
            richText: rsp.rich_text,
            timestamp: rsp.timestamp
        };
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
                    success: function() {
                        this.trigger('published');

                        if (_.isFunction(options.success)) {
                            options.success.call(context);
                        }
                    },
                    error: _.isFunction(options.error)
                           ? _.bind(options.error, context)
                           : undefined
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
