/*
 * Screenshots.
 */
RB.Screenshot = RB.BaseResource.extend({
    rspNamespace: 'screenshot',

    defaults: _.defaults({
        caption: null
    }, RB.BaseResource.prototype.defaults),

    toJSON: function() {
        return {
            caption: this.get('caption')
        };
    }
});
