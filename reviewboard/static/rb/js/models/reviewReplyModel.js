/*
 * Review replies.
 *
 * Encapsulates replies to a top-level review.
 */
RB.ReviewReply = RB.BaseResource.extend({
    defaults: _.defaults({
        review: null,
        public: false,
        bodyTop: null,
        bodyBottom: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'reply',
    listKey: 'replies',

    toJSON: function() {
        return {
            'public': this.get('public'),
            'body_top': this.get('bodyTop'),
            'body_bottom': this.get('bodyBottom')
        };
    },

    parse: function(rsp) {
        var result = RB.BaseResource.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.bodyTop = rspData.body_top;
        result.bodyBottom = rspData.body_bottom;
        result.public = rspData.public;

        return result;
    },
});
