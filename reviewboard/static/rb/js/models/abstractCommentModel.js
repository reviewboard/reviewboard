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

    parse: function(rsp) {
        var result = RB.AbstractResource.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.issueOpened = rspData.issue_opened;
        result.issueStatus = rspData.issue_status;
        result.text = rspData.text;

        return result;
    }
});
