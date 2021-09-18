/**
 * A review request.
 *
 * ReviewRequest is the starting point for much of the resource API. Through
 * it, the caller can create drafts, diffs, file attachments, and screenshots.
 *
 * Fields on a ReviewRequest are set by accessing the ReviewRequest.draft
 * object. Through there, fields can be set like any other model and then
 * saved.
 *
 * A review request can be closed by using the close() function, reopened
 * through reopen(), or even permanently destroyed by calling destroy().
 */
RB.ReviewRequest = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            approved: false,
            approvalFailure: null,
            branch: null,
            bugTrackerURL: null,
            bugsClosed: null,
            commitID: null,
            closeDescription: null,
            closeDescriptionRichText: false,
            dependsOn: [],
            description: null,
            descriptionRichText: false,
            draftReview: null,
            lastUpdated: null,
            localSitePrefix: null,
            'public': null,
            repository: null,
            reviewURL: null,
            state: null,
            summary: null,
            targetGroups: [],
            targetPeople: [],
            testingDone: null,
            testingDoneRichText: false
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'review_request',

    extraQueryArgs: {
        'force-text-type': 'html',
        'include-text-types': 'raw'
    },

    attrToJsonMap: {
        approvalFailure: 'approval_failure',
        bugsClosed: 'bugs_closed',
        closeDescription: 'close_description',
        closeDescriptionRichText: 'close_description_text_type',
        dependsOn: 'depends_on',
        descriptionRichText: 'description_text_type',
        lastUpdated: 'last_updated',
        reviewURL: 'url',
        targetGroups: 'target_groups',
        targetPeople: 'target_people',
        testingDone: 'testing_done',
        testingDoneRichText: 'testing_done_text_type'
    },

    deserializedAttrs: [
        'approved',
        'approvalFailure',
        'branch',
        'bugsClosed',
        'closeDescription',
        'dependsOn',
        'description',
        'lastUpdated',
        'public',
        'reviewURL',
        'summary',
        'targetGroups',
        'targetPeople',
        'testingDone'
    ],

    /**
     * Initialize the model.
     *
     * Args:
     *     attrs (object):
     *         Initial values for the model attributes.
     *
     *     options (object):
     *         Additional options for the object construction.
     *
     * Option Args:
     *     extraDraftAttrs (object):
     *         Additional attributes to include when creating a review request
     *         draft.
     */
    initialize(attrs, options={}) {
        RB.BaseResource.prototype.initialize.call(this, attrs, options);

        this.reviews = new Backbone.Collection([], {
            model: RB.Review
        });

        this.draft = new RB.DraftReviewRequest(_.defaults({
            parentObject: this,
            branch: this.get('branch'),
            bugsClosed: this.get('bugsClosed'),
            dependsOn: this.get('dependsOn'),
            description: this.get('description'),
            descriptionRichText: this.get('descriptionRichText'),
            summary: this.get('summary'),
            targetGroups: this.get('targetGroups'),
            targetPeople: this.get('targetPeople'),
            testingDone: this.get('testingDone'),
            testingDoneRichText: this.get('testingDoneRichText')
        }, options.extraDraftAttrs));
    },

    /**
     * Return the URL for syncing this model.
     *
     * Returns:
     *     string:
     *     The URL for the API resource.
     */
    url() {
        const url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                    'api/review-requests/';

        return this.isNew() ? url : `${url}${this.id}/`;
    },

    /**
     * Create the review request from an existing commit.
     *
     * This can only be used for new ReviewRequest instances, and requires
     * a commitID option.
     *
     * Version Changed:
     *     5.0:
     *     Changed the arguments to take the commit ID directly, and return a
     *     promise rather than use callbacks.
     *
     * Args:
     *     optionsOrCommitID (object or string):
     *         If invoking in a legacy mode, this is an object with callbacks.
     *         For new-style callers, this should be a string containing only
     *         the commit ID to create the review request from.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    createFromCommit(optionsOrCommitID={}, context={}) {
        if (_.isObject(optionsOrCommitID)) {
            console.assert(optionsOrCommitID.commitID);
            console.warn('RB.ReviewRequest.createFromCommit was called ' +
                         'using callbacks. Callers should be updated to ' +
                         'use promises instead.');
            return RB.promiseToCallbacks(optionsOrCommitID, context, () =>
                this.createFromCommit(optionsOrCommitID.commitID));
        }

        console.assert(optionsOrCommitID);
        console.assert(this.isNew());

        this.set('commitID', optionsOrCommitID);

        return this.save({ createFromCommit: true });
    },

    /**
     * Create a Diff object for this review request.
     *
     * Returns:
     *     RB.Diff:
     *     The new diff model.
     */
    createDiff() {
        return new RB.Diff({
            parentObject: this
        });
    },

    /**
     * Create a Review object for this review request.
     *
     * If an ID is specified, the Review object will reference that ID.
     * Otherwise, it is considered a draft review, and will either return
     * the existing one (if the draftReview attribute is set), or create
     * a new one (and set the attribute).
     *
     * Args:
     *     reviewID (number):
     *         The ID of the review, for existing reviews.
     *
     *     extraAttrs (object):
     *         Additional attributes to set on new models.
     *
     * Returns:
     *     RB.Review:
     *     The new review object.
     */
    createReview(reviewID, extraAttrs={}) {
        let review;

        if (reviewID === undefined) {
            review = this.get('draftReview');

            if (review === null) {
                review = new RB.DraftReview({
                    parentObject: this
                });

                this.set('draftReview', review);
            }
        } else {
            review = this.reviews.get(reviewID);

            if (!review) {
                review = new RB.Review(_.defaults({
                    parentObject: this,
                    id: reviewID
                }, extraAttrs));
                this.reviews.add(review);
            }

        }

        return review;
    },

    /**
     * Create a Screenshot object for this review request.
     *
     * Args:
     *     screenshotID (number):
     *         The ID of the screenshot, for existing screenshots.
     *
     * Returns:
     *     RB.Screenshot:
     *     The new screenshot object.
     */
    createScreenshot(screenshotID) {
        return new RB.Screenshot({
            parentObject: this,
            id: screenshotID
        });
    },

    /**
     * Create a FileAttachment object for this review request.
     *
     * Args:
     *     attributes (object):
     *         Additional attributes to include on the new model.
     *
     * Returns:
     *     RB.FileAttachment:
     *     The new file attachment object.
     */
    createFileAttachment(attributes) {
        return new RB.FileAttachment(_.defaults({
            parentObject: this
        }, attributes));
    },

    /**
     * Mark a review request as starred or unstarred.
     *
     * Args:
     *     starred (boolean):
     *         Whether the review request is starred.
     *
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    setStarred(starred, options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewRequest.setStarred was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.setStarred(starred));
        }

        const watched = RB.UserSession.instance.watchedReviewRequests;
        return starred ? watched.addImmediately(this)
                       : watched.removeImmediately(this);
    },

    /**
     * Close the review request.
     *
     * A 'type' option must be provided, which must match one of the
     * close types (ReviewRequest.CLOSE_DISCARDED or
     * ReviewRequest.CLOSE_SUBMITTED).
     *
     * An optional description can be set by passing a 'description' option.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async close(options, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewRequest.close was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.close(newOptions));
        }

        const data = {};

        console.assert(options);

        if (options.type === RB.ReviewRequest.CLOSE_DISCARDED) {
            data.status = 'discarded';
        } else if (options.type === RB.ReviewRequest.CLOSE_SUBMITTED) {
            data.status = 'submitted';
        } else {
            return Promise.reject(new Error('Invalid close type'));
        }

        if (options.description !== undefined) {
            data.close_description = options.description;
        }

        if (options.richText !== undefined) {
            data.close_description_text_type =
                (options.richText ? 'markdown' : 'plain');
        }

        if (options.postData !== undefined) {
            _.extend(data, options.postData);
        }

        const changingState = (options.type !== this.get('state'));

        const saveOptions = _.defaults({
            data: data,
        }, options);

        delete saveOptions.type;
        delete saveOptions.description;

        await this.save(saveOptions);

        if (changingState) {
            this.trigger('closed');
        }

        this.markUpdated(this.get('lastUpdated'));
    },

    /**
     * Reopen the review request.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async reopen(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewRequest.reopen was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.reopen());
        }

        await this.save({
            data: {
                status: 'pending',
            },
        });

        this.trigger('reopened');
        this.markUpdated(this.get('lastUpdated'));
    },

    /**
     * Marks the review request as having been updated at the given timestamp.
     *
     * This should be used when an action will trigger an update to the
     * review request's Last Updated timestamp, but where we don't want
     * a notification later on. The local copy of the timestamp can be
     * bumped to mark it as up-to-date.
     *
     * Args:
     *     timestamp (string):
     *         The timestamp to store.
     */
    markUpdated(timestamp) {
        this._lastUpdateTimestamp = timestamp;
    },

    /**
     * Begin checking for server-side updates to the review request.
     *
     * The 'updated' event will be triggered when there's a new update.
     *
     * Args:
     *     type (string):
     *         The type of updates to check for.
     *
     *     lastUpdateTimestamp (string):
     *         The timestamp of the last known update.
     */
    async beginCheckForUpdates(type, lastUpdateTimestamp) {
        this._checkUpdatesType = type;
        this._lastUpdateTimestamp = lastUpdateTimestamp;

        await this.ready();
        setTimeout(this._checkForUpdates.bind(this),
                   RB.ReviewRequest.CHECK_UPDATES_MSECS);
    },

    /**
     * Check for updates.
     *
     * This is called periodically after an initial call to
     * beginCheckForUpdates. It will see if there's a new update yet on the
     * server, and if there is, trigger the 'updated' event.
     */
    _checkForUpdates() {
        RB.apiCall({
            type: 'GET',
            prefix: this.get('sitePrefix'),
            noActivityIndicator: true,
            url: this.get('links').last_update.href,
            success: rsp => {
                const lastUpdate = rsp.last_update;

                if ((!this._checkUpdatesType ||
                     this._checkUpdatesType === lastUpdate.type) &&
                    this._lastUpdateTimestamp !== lastUpdate.timestamp) {
                    this.trigger('updated', lastUpdate);
                }

                this._lastUpdateTimestamp = lastUpdate.timestamp;

                setTimeout(this._checkForUpdates.bind(this),
                           RB.ReviewRequest.CHECK_UPDATES_MSECS);
            }
        });
    },

    /**
     * Serialize for sending to the server.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     * Option Args:
     *     createFromCommit (boolean):
     *         Whether this save is going to create a new review request from
     *         an existing committed change.
     *
     * Returns:
     *     object:
     *     Data suitable for passing to JSON.stringify.
     */
    toJSON(options={}) {
        if (this.isNew()) {
            const commitID = this.get('commitID');
            const repository = this.get('repository');
            const result = {};

            if (commitID) {
                result.commit_id = commitID;

                if (options.createFromCommit) {
                    result.create_from_commit_id = true;
                }
            }

            if (repository) {
                result.repository = repository;
            }

            return result;
        } else {
            return _super(this).toJSON.apply(this, arguments);
        }
    },

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(rsp) {
        const state = {
            pending: RB.ReviewRequest.PENDING,
            discarded: RB.ReviewRequest.CLOSE_DISCARDED,
            submitted: RB.ReviewRequest.CLOSE_SUBMITTED
        }[rsp.status];
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.state = state;
        data.closeDescriptionRichText =
            (rawTextFields.close_description_text_type === 'markdown');
        data.descriptionRichText =
            (rawTextFields.description_text_type === 'markdown');
        data.testingDoneRichText =
            (rawTextFields.testing_done_text_type === 'markdown');

        return data;
    }
}, {
    CHECK_UPDATES_MSECS: 5 * 60 * 1000, // Every 5 minutes

    CLOSE_DISCARDED: 1,
    CLOSE_SUBMITTED: 2,
    PENDING: 3,

    VISIBILITY_VISIBLE: 1,
    VISIBILITY_ARCHIVED: 2,
    VISIBILITY_MUTED: 3
});
