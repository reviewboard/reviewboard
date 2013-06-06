RB.AbstractComment = RB.AbstractResource.extend({
    defaults: _.defaults({
        issueOpened: true,
        issueStatus: '',
        text: ''
    }, RB.AbstractResource.prototype.defaults),

    destroyIfEmpty: function(options) {
        if (!this.get('text')) {
            this.destroy(options);
        }
    },

    toJSON: function() {
        var data = {
            text: this.get('text'),
            issue_opened: this.get('issueOpened')
        };

        if (this.get('loaded') && this.get('parentObject').get('public')) {
            data.issue_status = this.get('issueState');
        }

        return data;
    },

    parseResourceData: function(rsp) {
        return {
            issueOpened: rsp.issue_opened,
            issueStatus: rsp.issue_status,
            text: rsp.text
        };
    }
});
