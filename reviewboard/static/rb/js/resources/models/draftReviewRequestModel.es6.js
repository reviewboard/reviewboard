/**
 * The draft of a review request.
 *
 * This provides editing capabilities for a review request draft, as well
 * as the ability to publish and discard (destroy) a draft.
 */
RB.DraftReviewRequest = RB.BaseResource.extend(_.defaults({
    defaults() {
        return _.defaults({
            branch: null,
            bugsClosed: null,
            changeDescription: null,
            changeDescriptionRichText: false,
            dependsOn: [],
            description: null,
            descriptionRichText: false,
            'public': null,
            rawTextFields: null,
            submitter: null,
            summary: null,
            targetGroups: [],
            targetPeople: [],
            testingDone: null,
            testingDoneRichText: false
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'draft',
    listKey: 'draft',
    supportsExtraData: true,

    expandedFields: ['depends_on', 'target_people', 'target_groups'],

    extraQueryArgs: {
        'force-text-type': 'html',
        'include-text-types': 'raw'
    },

    attrToJsonMap: {
        bugsClosed: 'bugs_closed',
        changeDescription: 'changedescription',
        changeDescriptionRichText: 'changedescription_text_type',
        dependsOn: 'depends_on',
        descriptionRichText: 'description_text_type',
        targetGroups: 'target_groups',
        targetPeople: 'target_people',
        testingDone: 'testing_done',
        testingDoneRichText: 'testing_done_text_type'
    },

    deserializedAttrs: [
        'branch',
        'bugsClosed',
        'changeDescription',
        'dependsOn',
        'description',
        'public',
        'summary',
        'targetGroups',
        'targetPeople',
        'testingDone'
    ],

    /**
     * Return the URL to use when syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to sync.
     */
    url() {
        return this.get('parentObject').get('links').draft.href;
    },

    /**
     * Create a FileAttachment object for this draft.
     *
     * Args:
     *     attributes (object):
     *         Attributes for the file attachment model.
     *
     * Returns:
     *     RB.DraftFileAttachment:
     *     The new file attachment object.
     */
    createFileAttachment(attributes) {
        return new RB.DraftFileAttachment(_.defaults({
            parentObject: this
        }, attributes));
    },

    /**
     * Publish the draft.
     *
     * The contents of the draft will be validated before being sent to the
     * server in order to ensure that the appropriate fields are all there.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated the callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for the operation, including callbacks.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async publish(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DraftReview.publish was called using callbacks. ' +
                         'Callers should be updated to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.publish(newOptions));
        }

        await this.ready();

        const validationError = this.validate(this.attributes, {
            publishing: true,
        });

        if (validationError) {
            throw new BackboneError(
                this, { errorText: validationError }, options);
        }

        await this.save(_.defaults({
            data: {
                'public': 1,
                trivial: options.trivial ? 1 : 0
            }
        }, options));
    },

    parseResourceData(rsp) {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.submitter = rsp.links.submitter;
        data.changeDescriptionRichText =
            (rawTextFields.changedescription_text_type === 'markdown');
        data.descriptionRichText =
            (rawTextFields.description_text_type === 'markdown');
        data.testingDoneRichText =
            (rawTextFields.testing_done_text_type === 'markdown');
        data.rawTextFields = rawTextFields || null;

        return data;
    }
}, RB.DraftResourceModelMixin));
