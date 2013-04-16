/*
 * The draft of a review request.
 *
 * This provides editing capabilities for a review request draft, as well
 * as the ability to publish and discard (destroy) a draft.
 */
RB.DraftReviewRequest = RB.BaseResource.extend(_.defaults({
    defaults: _.defaults({
        branch: null,
        bugsClosed: null,
        changeDescription: null,
        description: null,
        public: null,
        summary: null,
        targetGroups: null,
        targetPeople: null,
        testingDone: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'draft',
    listKey: 'draft',

    expandedFields: ['target_people', 'target_groups'],

    url: function() {
        return this.get('parentObject').get('links').draft.href;
    },

    /*
     * Publishes the draft.
     */
    publish: function(options, context) {
        this.save(
            _.defaults({
                data: {
                    public: 1
                }
            }, options),
            context);
    },

    parse: function(rsp) {
        var result = RB.BaseResource.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.branch = rspData.branch;
        result.bugsClosed = rspData.bugs_closed;
        result.changeDescription = rspData.change_description;
        result.description = rspData.description;
        result.public = rspData.public;
        result.summary = rspData.summary;
        result.targetGroups = rspData.target_groups;
        result.targetPeople = rspData.target_people;
        result.testingDone = rspData.testing_done;

        return result;
    },

    sync: function(method, model, options) {
        /*
         * Expand certain fields so that we can be sure that the values
         * will be what we expect whether we're updating or getting.
         */
        options.data = _.defaults({
            expand: this.expandedFields.join(',')
        }, options.data);

        return RB.BaseResource.prototype.sync.call(this, method, model,
                                                   options);
    }
}, RB.DraftResourceModelMixin));
