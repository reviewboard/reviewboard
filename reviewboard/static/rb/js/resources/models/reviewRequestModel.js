/*
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
    defaults: function() {
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

    initialize: function(attrs, options) {
        options = options || {};

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

    url: function() {
        var url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/review-requests/';

        if (!this.isNew()) {
            url += this.id + '/';
        }

        return url;
    },

    /*
     * Creates the review request from an existing commit.
     *
     * This can only be used for new ReviewRequest instances, and requires
     * a commitID option.
     */
    createFromCommit: function(options, context) {
        console.assert(options.commitID);
        console.assert(this.isNew());

        this.set('commitID', options.commitID);
        this.save(
            _.extend({
                createFromCommit: true
            }, options),
            context);
    },

    /*
     * Creates a Diff object for this review request.
     */
    createDiff: function() {
        return new RB.Diff({
            parentObject: this
        });
    },

    /*
     * Creates a Review object for this review request.
     *
     * If an ID is specified, the Review object will reference that ID.
     * Otherwise, it is considered a draft review, and will either return
     * the existing one (if the draftReview attribute is set), or create
     * a new one (and set the attribute).
     */
    createReview: function(reviewID) {
        var review;

        if (reviewID === undefined) {
            review = this.get('draftReview');

            if (review === null) {
                review = new RB.DraftReview({
                    parentObject: this
                });

                this.set('draftReview', review);
            }

            return review;
        } else {
            review = this.reviews.get(reviewID);

            if (!review) {
                review = new RB.Review({
                    parentObject: this,
                    id: reviewID
                });
                this.reviews.add(review);
            }
        }

        return review;
    },

    /*
     * Creates a Screenshot object for this review request.
     */
    createScreenshot: function(screenshotID) {
        return new RB.Screenshot({
            parentObject: this,
            id: screenshotID
        });
    },

    /*
     * Creates a FileAttachment object for this review request.
     */
    createFileAttachment: function(attributes) {
        return new RB.FileAttachment(_.defaults({
            parentObject: this
        }, attributes));
    },

    /*
     * Marks a review request as starred or unstarred.
     */
    setStarred: function(starred, options, context) {
        var watched = RB.UserSession.instance.watchedReviewRequests;

        if (starred) {
            watched.addImmediately(this, options, context);
        } else {
            watched.removeImmediately(this, options, context);
        }
    },

    /*
     * Closes the review request.
     *
     * A 'type' option must be provided, which must match one of the
     * close types (ReviewRequest.CLOSE_DISCARDED or
     * ReviewRequest.CLOSE_SUBMITTED).
     *
     * An optional description can be set by passing a 'description' option.
     */
    close: function(options, context) {
        var data = {},
            changingState,
            saveOptions;

        console.assert(options);

        if (options.type === RB.ReviewRequest.CLOSE_DISCARDED) {
            data.status = 'discarded';
        } else if (options.type === RB.ReviewRequest.CLOSE_SUBMITTED) {
            data.status = 'submitted';
        } else {
            if (_.isFunction(options.error)) {
                options.error.call(this, {
                    errorText: 'Invalid close type'
                });
            }

            return;
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

        changingState = (options.type !== this.get('state'));

        saveOptions = _.defaults({
            data: data,

            success: _.bind(function() {
                if (changingState) {
                    this.trigger('closed');
                }

                this.markUpdated(this.get('lastUpdated'));

                if (_.isFunction(options.success)) {
                    options.success.call(context);
                }
            }, this)
        }, options);

        delete saveOptions.type;
        delete saveOptions.description;

        this.save(saveOptions, context);
    },

    /*
     * Reopens the review request.
     */
    reopen: function(options, context) {
        options = options || {};

        this.save(
            _.defaults({
                data: {
                    status: 'pending'
                },

                success: _.bind(function() {
                    this.trigger('reopened');
                    this.markUpdated(this.get('lastUpdated'));

                    if (_.isFunction(options.success)) {
                        options.success.call(context);
                    }
                }, this)
            }, options),
            context);
    },

    /*
     * Marks the review request as having been updated at the given timestamp.
     *
     * This should be used when an action will trigger an update to the
     * review request's Last Updated timestamp, but where we don't want
     * a notification later on. The local copy of the timestamp can be
     * bumped to mark it as up-to-date.
     */
    markUpdated: function(timestamp) {
        this._lastUpdateTimestamp = timestamp;
    },

    /*
     * Begins checking for server-side updates to the review request.
     *
     * This takes a type of update to check for, and the last known
     * updated timestamp.
     *
     * The 'updated' event will be triggered when there's a new update.
     */
    beginCheckForUpdates: function(type, lastUpdateTimestamp) {
        this._checkUpdatesType = type;
        this._lastUpdateTimestamp = lastUpdateTimestamp;

        this.ready({
            ready: function() {
                setTimeout(_.bind(this._checkForUpdates, this),
                           RB.ReviewRequest.CHECK_UPDATES_MSECS);
            }
        }, this);
    },

    /*
     * Checks for updates.
     *
     * This is called periodically after an initial call to
     * beginCheckForUpdates. It will see if there's a new update yet on the
     * server, and if there is, trigger the 'updated' event.
     */
    _checkForUpdates: function() {
        RB.apiCall({
            type: 'GET',
            prefix: this.get('sitePrefix'),
            noActivityIndicator: true,
            url: this.get('links').last_update.href,
            success: _.bind(function(rsp) {
                var lastUpdate = rsp.last_update;
                if ((this._checkUpdatesType === undefined ||
                     this._checkUpdatesType === lastUpdate.type) &&
                    this._lastUpdateTimestamp !== lastUpdate.timestamp) {
                    this.trigger('updated', lastUpdate);
                }

                this._lastUpdateTimestamp = lastUpdate.timestamp;

                setTimeout(_.bind(this._checkForUpdates, this),
                           RB.ReviewRequest.CHECK_UPDATES_MSECS);
            }, this)
        });
    },

    /*
     * Serialize for sending to the server.
     */
    toJSON: function(options) {
        var commitID = this.get('commitID'),
            repository = this.get('repository'),
            result = {};

        options = options || {};

        if (this.isNew()) {
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

    /*
     * Deserialize the response from the server.
     */
    parseResourceData: function(rsp) {
        var state = {
                pending: RB.ReviewRequest.PENDING,
                discarded: RB.ReviewRequest.CLOSE_DISCARDED,
                submitted: RB.ReviewRequest.CLOSE_SUBMITTED
            }[rsp.status],
            rawTextFields = rsp.raw_text_fields || rsp,
            data = RB.BaseResource.prototype.parseResourceData.call(this, rsp);

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
    PENDING: 3
});
