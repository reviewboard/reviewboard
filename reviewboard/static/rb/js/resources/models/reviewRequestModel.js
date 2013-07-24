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
    defaults: _.defaults({
        branch: null,
        bugTrackerURL: null,
        bugsClosed: null,
        commitID: null,
        changeDescription: null,
        dependsOn: [],
        description: null,
        draftReview: null,
        localSitePrefix: null,
        public: null,
        repository: null,
        reviewURL: null,
        summary: null,
        targetGroups: [],
        targetPeople: [],
        testingDone: null
    }),

    rspNamespace: 'review_request',

    initialize: function() {
        RB.BaseResource.prototype.initialize.apply(this, arguments);

        this.reviews = new Backbone.Collection([], {
            model: RB.Review
        });

        this.draft = new RB.DraftReviewRequest({
            parentObject: this,
            branch: this.get('branch'),
            bugsClosed: this.get('bugsClosed'),
            changeDescription: this.get('changeDescription'),
            dependsOn: this.get('dependsOn'),
            description: this.get('description'),
            summary: this.get('summary'),
            targetGroups: this.get('targetGroups'),
            targetPeople: this.get('targetPeople'),
            testingDone: this.get('testingDone')
        });
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
        var data = {};

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
            data.description = options.description;
        }

        options = _.defaults({
            data: data
        }, options);

        delete options.type;
        delete options.description;

        this.save(options, context);
    },

    /*
     * Reopens the review request.
     */
    reopen: function(options, context) {
        this.save(
            _.defaults({
                data: {
                    status: 'pending'
                }
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
    toJSON: function() {
        var commitID = this.get('commitID'),
            repository = this.get('repository'),
            result = {};

        if (this.isNew()) {
            if (commitID) {
                result.commit_id = commitID;
            }
            if (repository) {
                result.repository = repository;
            }
            return result;
        } else {
            return _.super(this).toJSON.apply(this, arguments);
        }
    },

    /*
     * Deserialize the response from the server.
     */
    parseResourceData: function(rsp) {
        return {
            branch: rsp.branch,
            bugsClosed: rsp.bugs_closed,
            dependsOn: rsp.depends_on,
            description: rsp.description,
            public: rsp.public,
            reviewURL: rsp.url,
            summary: rsp.summary,
            targetGroups: rsp.target_groups,
            targetPeople: rsp.target_people,
            testingDone: rsp.testing_done
        };
    }
}, {
    CHECK_UPDATES_MSECS: 5 * 60 * 1000, // Every 5 minutes

    CLOSE_DISCARDED: 1,
    CLOSE_SUBMITTED: 2
});
