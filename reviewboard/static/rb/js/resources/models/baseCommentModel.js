/*
 * The base model for a comment.
 *
 * This provides all the common properties, serialization, deserialization,
 * validation, and other functionality of comments. It's meant to be
 * subclassed by more specific implementations.
 */
RB.BaseComment = RB.BaseResource.extend({
    defaults: _.defaults({
        /* Extra data for the comment. */
        extraData: {},

        /* Whether or not an issue is opened. */
        issueOpened: true,

        /*
         * The current state of the issue.
         *
         * This must be one of STATE_DROPPED, STATE_OPEN, or STATE_RESOLVED.
         */
        issueStatus: null,

        /* Whether the comment is saved in rich-text (Markdown) format. */
        richText: false,

        /* The text entered for the comment. */
        text: ''
    }, RB.BaseResource.prototype.defaults),

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
     * Serializes the comment to a payload that can be sent to the server.
     *
     * This must be overloaded by subclasses, and the parent version called.
     */
    toJSON: function() {
        var data = {
                issue_opened: this.get('issueOpened'),
                rich_text: this.get('richText'),
                text: this.get('text')
            },
            parentObject,
            isPublic;

        _.each(this.get('extraData'), function(value, key) {
            data['extra_data.' + key] = value;
        }, this);

        if (this.get('loaded')) {
            parentObject = this.get('parentObject');

            /*
             * XXX This is temporary to support older-style resource
             *     objects. We should just use get() once we're moved
             *     entirely onto BaseResource.
             */
            isPublic = parentObject.cid
                       ? parentObject.get('public')
                       : parentObject.public;

            if (isPublic) {
                data.issue_status = this.get('issueStatus');
            }
        }

        return data;
    },

    /*
     * Deserializes comment data from an API payload.
     *
     * This must be overloaded by subclasses, and the parent version called.
     */
    parseResourceData: function(rsp) {
        return {
            extraData: rsp.extra_data,
            issueOpened: rsp.issue_opened,
            issueStatus: rsp.issue_status,
            richText: rsp.rich_text,
            text: rsp.text
        };
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
