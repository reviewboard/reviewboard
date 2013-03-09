/*
 * Review replies.
 *
 * Encapsulates replies to a top-level review.
 */
RB.ReviewReply = RB.BaseResource.extend({
    /*
     * TODO: body_top and body_bottom should really be camelCase, but that's
     * a little hard to do until we convert Review to be a Backbone.js Model.
     */
    defaults: _.defaults({
        review: null,
        public: false,
        body_top: null,
        body_bottom: null
    }, RB.BaseResource.defaults),

    rspNamespace: 'reply',
    listKey: 'replies',

    toJSON: function() {
        return {
            'public': this.get('public'),
            'body_top': this.get('body_top'),
            'body_bottom': this.get('body_bottom')
        };
    },

    parse: function(rsp) {
        var result = RB.BaseResource.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.body_top = rspData.body_top;
        result.body_bottom = rspData.body_bottom;
        result.public = rspData.public;

        return result;
    },
});
