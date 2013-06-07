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
        dependsOn: [],
        description: null,
        public: null,
        summary: null,
        targetGroups: [],
        targetPeople: [],
        testingDone: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'draft',
    listKey: 'draft',

    expandedFields: ['depends_on', 'target_people', 'target_groups'],

    url: function() {
        return this.get('parentObject').get('links').draft.href;
    },

    /*
     * Publishes the draft.
     *
     * The contents of the draft will be validated before being sent to the
     * server in order to ensure that the appropriate fields are all there.
     */
    publish: function(options, context) {
        options = options || {};

        this.ready({
            ready: function() {
                var validationError = this.validate(this.attributes, {
                    publishing: true
                });

                if (validationError) {
                    if (_.isFunction(options.error)) {
                        options.error.call(context, {
                            errorText: validationError
                        });
                    }
                } else {
                    this.save(
                        _.defaults({
                            data: {
                                public: 1
                            }
                        }, options),
                        context);
                }
            },
            error: _.isFunction(options.error)
                   ? _.bind(options.error, context)
                   : undefined
        }, this);
    },

    validate: function(attrs, options) {
        if (options.publishing) {
            if (attrs.targetGroups.length === 0 &&
                attrs.targetPeople.length === 0) {
                return RB.DraftReviewRequest.strings.REVIEWERS_REQUIRED;
            }

            if ($.trim(attrs.summary) === '') {
                return RB.DraftReviewRequest.strings.SUMMARY_REQUIRED;
            }

            if ($.trim(attrs.description) === '') {
                return RB.DraftReviewRequest.strings.DESCRIPTION_REQUIRED;
            }
        }
    },

    parse: function(rsp) {
        var result = RB.BaseResource.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.branch = rspData.branch;
        result.bugsClosed = rspData.bugs_closed;
        result.changeDescription = rspData.change_description;
        result.dependsOn = rspData.depends_on;
        result.description = rspData.description;
        result.public = rspData.public;
        result.summary = rspData.summary;
        result.targetGroups = rspData.target_groups;
        result.targetPeople = rspData.target_people;
        result.testingDone = rspData.testing_done;

        return result;
    }
}, RB.DraftResourceModelMixin),
{
    strings: {
        DESCRIPTION_REQUIRED: 'The draft must have a description.',
        REVIEWERS_REQUIRED: 'There must be at least one reviewer before this ' +
                            'review request can be published.',
        SUMMARY_REQUIRED: 'The draft must have a summary.'
    }
});
