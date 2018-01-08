/**
 * Model for the review request page.
 *
 * This manages state specific to the review request page, and handles
 * watching for server-side updates relevant to entries and UI on the page.
 */
RB.ReviewRequestPage.ReviewRequestPage = RB.ReviewablePage.extend({
    defaults: _.defaults({
        updatesURL: null,
    }, RB.ReviewablePage.prototype.defaults),

    /**
     * Initialize the model.
     */
    initialize() {
        RB.ReviewablePage.prototype.initialize.apply(this, arguments);

        this._watchedEntries = {};
        this._watchedUpdatesPeriodMS = null;
        this._watchedUpdatesTimeout = null;
        this._watchedUpdatesLastScheduleTime = null;

        this.entries = new Backbone.Collection([], {
            model: RB.ReviewRequestPage.Entry,
        });
    },

    /**
     * Parse the data for the page.
     *
     * This will take data from the server and turn it into a series of
     * objects and attributes needed for parts of the page.
     *
     * Args:
     *     rsp (object):
     *         The incoming data provided for the page.
     *
     * Returns:
     *     object:
     *     The resulting attributes for the page.
     */
    parse(rsp) {
        return _.extend({
            updatesURL: rsp.updatesURL,
        }, RB.ReviewablePage.prototype.parse.call(this, rsp));
    },

    /**
     * Add an entry to the page.
     *
     * The entry's ``page`` attribute will be set to this page, for reference,
     * and then the entry will be added to the ``entries`` collection.
     *
     * Args:
     *     entry (RB.ReviewRequestPage.Entry):
     *         The entry to add.
     */
    addEntry(entry) {
        entry.set('page', this);
        this.entries.add(entry);
    },

    /**
     * Watch for updates to an entry.
     *
     * The entry will be checked for updates at least once every ``periodMS``
     * milliseconds.
     *
     * Args:
     *     entry (RB.ReviewRequestPage.Entry):
     *         The entry being watched for updates.
     *
     *     periodMS (number):
     *         The frequency at which the updates should be polled. Updates
     *         will be checked at least this often.
     */
    watchEntryUpdates(entry, periodMS) {
        /*
         * If we already have a check in progress, and this new update
         * request wants to check sooner than the current check is scheduled,
         * then disconnect the old timer so we can reconnect it with the new
         * delay.
         */
        if (this._watchedUpdatesPeriodMS === null ||
            periodMS < this._watchedUpdatesPeriodMS) {
            /*
             * This is either the only update requested, or it's more frequent
             * than other ones. Now we just need to check if we need to cancel
             * any previous update checks that are scheduled later than the
             * new check would be.
             */
            if (this._watchedUpdatesTimeout !== null &&
                (Date.now() -
                 this._watchedUpdatesLastScheduleTime) > periodMS) {
                clearTimeout(this._watchedUpdatesTimeout);
                this._watchedUpdatesTimeout = null;
            }

            this._watchedUpdatesPeriodMS = periodMS;
        }

        this._watchedEntries[entry.id] = {
            entry: entry,
            periodMS: periodMS,
        };

        this._scheduleCheckUpdates();
    },

    /**
     * Stop watching for updates to an entry.
     *
     * Args:
     *     entry (RB.ReviewRequestPage.Entry):
     *         The entry being watched for updates.
     */
    stopWatchingEntryUpdates(entry) {
        if (!this._watchedEntries.hasOwnProperty(entry.id)) {
            return;
        }

        delete this._watchedEntries[entry.id];

        /*
         * We'll either be clearing this for now, or recomputing. Either way,
         * we want this null for the next steps.
         */
        this._watchedUpdatesPeriodMS = null;

        if (_.isEmpty(this._watchedEntries)) {
            /*
             * There's nothing left to watch, so cancel the timeout (if set)
             * and clear state.
             */
            if (this._watchedUpdatesTimeout !== null) {
                clearTimeout(this._watchedUpdatesTimeout);
                this._watchedUpdatesTimeout = null;
            }

            this._watchedUpdatesLastScheduleTime = null;
        } else {
            /*
             * There's still other entries being watched. We need to
             * update state accordingly.
             *
             * We'll let any current timeouts continue as-is.
             */
            for (let key in this._watchedEntries) {
                if (this._watchedEntries.hasOwnProperty(key)) {
                    const periodMS = this._watchedEntries[key].periodMS;

                    this._watchedUpdatesPeriodMS =
                        (this._watchedUpdatesPeriodMS === null
                         ? periodMS
                         : Math.min(this._watchedUpdatesPeriodMS, periodMS));
                }
            }
        }
    },

    /**
     * Schedule the next updates check.
     *
     * The check will only be scheduled so long as there are still entries
     * being watched. Any data returned in the check will trigger reloads
     * of parts of the page.
     */
    _scheduleCheckUpdates() {
        if (this._watchedUpdatesTimeout !== null ||
            this._watchedUpdatesPeriodMS === null) {
            return;
        }

        this._watchedUpdatesLastScheduleTime = Date.now();
        this._watchedUpdatesTimeout = setTimeout(
            () => {
                this._watchedUpdatesTimeout = null;
                this._loadUpdates({
                    entries: _.pluck(this._watchedEntries, 'entry'),
                    onDone: this._scheduleCheckUpdates.bind(this),
                });
            },
            this._watchedUpdatesPeriodMS);
    },

    /**
     * Load updates from the server.
     *
     * Args:
     *     options (object, optional):
     *         Options that control the types of updates loaded from the
     *         server.
     *
     * Option Args:
     *     entries (Array):
     *         A list of entry models that need to be checked for updates.
     *
     *     onDone (function, optional):
     *         Optional function to call after everything is loaded.
     */
    _loadUpdates(options={}) {
        const updatesURL = this.get('updatesURL');
        const allEntryIDs = {};
        const entries = options.entries || [];

        const urlQuery = [];

        if (entries.length > 0) {
            for (let i = 0; i < entries.length; i++) {
                const entry = entries[i];
                const typeID = entry.get('typeID');

                if (!allEntryIDs.hasOwnProperty(typeID)) {
                    allEntryIDs[typeID] = [];
                }

                allEntryIDs[typeID].push(entry.id);
            }

            const urlEntryTypeIDs = [];

            for (let entryTypeID in allEntryIDs) {
                if (allEntryIDs.hasOwnProperty(entryTypeID)) {
                    /*
                     * Sort the IDs numerically, so that we have a stable URL
                     * for caching.
                     */
                    allEntryIDs[entryTypeID].sort((a, b) => a - b);

                    const entryIDs = allEntryIDs[entryTypeID].join(',');
                    urlEntryTypeIDs.push(`${entryTypeID}:${entryIDs}`);
                }
            }

            urlQuery.push(`entries=${urlEntryTypeIDs.join(';')}`);
        }

        /*
         * Like above, sort the URL queries, so that we have a stable URL
         * for caching.
         */
        urlQuery.sort();

        const urlQueryStr = (urlQuery.length > 0
                             ? `?${urlQuery.join('&')}`
                             : '');

        Backbone.sync(
            'read',
            this,
            {
                url: `${updatesURL}${urlQueryStr}`,
                dataType: 'arraybuffer',
                noActivityIndicator: true,
                success: arrayBuffer => this._processUpdatesFromPayload(
                    arrayBuffer, options.onDone),
            });
    },

    /**
     * Process an updates payload from the server.
     *
     * This will parse the payload and then update each of the entries
     * or other parts of the UI referenced.
     *
     * Args:
     *     arrayBuffer (ArrayBuffer):
     *         The array buffer being parsed.
     *
     *     onDone (function, optional):
     *         The function to call when all updates have been parsed and
     *         applied.
     */
    _processUpdatesFromPayload(arrayBuffer, onDone) {
        const dataView = new DataView(arrayBuffer);
        const len = dataView.byteLength;
        let pos = 0;
        let totalUpdates = 0;
        let totalApplied = 0;
        let done = false;

        const onUpdateLoaded = (metadata, html) => {
            /*
             * Based on the update, we can now start updating the UI, if
             * we can find the matching entry or UI component.
             */
            if (metadata.type === 'entry') {
                this._processEntryUpdate(metadata, html);
            } else {
                this._reloadFromUpdate(null, metadata, html);
            }

            totalApplied++;

            if (done && totalApplied === totalUpdates) {
                this.trigger('updatesProcessed');

                if (_.isFunction(onDone)) {
                    onDone();
                }
            }
        };

        while (!done) {
            const parsed = this._processUpdateFromPayload(arrayBuffer,
                                                          dataView,
                                                          pos);

            totalUpdates++;
            pos = parsed.pos;
            done = (pos >= len);

            parsed.load(onUpdateLoaded);
        }
    },

    /**
     * Process a single update from the updates payload.
     *
     * This will parse out the details for one update, loading in the metadata
     * and HTML, and then apply that update.
     *
     * Args:
     *     arrayBuffer (ArrayBuffer):
     *         The array buffer being parsed.
     *
     *     dataView (DataView):
     *         The data view on top of the array buffer, used to extract
     *         information.
     *
     *     pos (number):
     *         The current position within the array buffer.
     *
     * Returns:
     *     object:
     *     An object with two keys:
     *
     *     ``pos``:
     *         The next position to parse.
     *
     *     ``load``:
     *         A function for loading the update content. This takes a
     *         callback function as an argument containing ``metadata`` and
     *         ``html`` arguments.
     */
    _processUpdateFromPayload(arrayBuffer, dataView, pos) {
        /* Read the length of the metadata. */
        const metadataLen = dataView.getUint32(pos, true);
        pos += 4;

        /* Read the start position of the metadata content for later. */
        const metadataStart = pos;
        pos += metadataLen;

        /* Read the length of the HTML content. */
        const htmlLen = dataView.getUint32(pos, true);
        pos += 4;

        /* Read the start position of the HTML content for later. */
        const htmlStart = pos;
        pos += htmlLen;

        return {
            pos: pos,
            load(cb) {
                const metadataBlob = new Blob([
                    arrayBuffer.slice(metadataStart,
                                      metadataStart + metadataLen),
                ]);
                const htmlBlob = new Blob([
                    arrayBuffer.slice(htmlStart, htmlStart + htmlLen),
                ]);

                RB.DataUtils.readManyBlobsAsStrings(
                    [metadataBlob, htmlBlob],
                    (metadata, html) => cb(JSON.parse(metadata), html));
            },
        };
    },

    /**
     * Process the update to an entry.
     *
     * This will locate the existing entry on the page, check if it needs
     * updating, and then update the entry's attributes and HTML.
     *
     * Args:
     *     metadata (object):
     *         The metadata for the entry update.
     *
     *     html (string):
     *         The new HTML for the entry.
     */
    _processEntryUpdate(metadata, html) {
        /*
         * TODO: We'll eventually want to handle new entries we don't
         *       know about. This would be part of a larger dynamic
         *       page updates change.
         */
        const entry = this.entries.get(metadata.entryID);

        if (!entry) {
            return;
        }

        console.assert(entry.get('typeID') === metadata.entryType);

        /* Only reload this entry if its updated timestamp has changed. */
        const newTimestamp = new Date(metadata.updatedTimestamp);

        if (newTimestamp <= entry.get('updatedTimestamp')) {
            return;
        }

        this._reloadFromUpdate(entry, metadata, html);
    },

    /**
     * Reload a component's attributes and HTML based on an update.
     *
     * This will update the attributes for a model, notifying listeners of
     * each stage of the update so that models and views can react
     * appropriately.
     *
     * If the model has ``beforeApplyUpdate`` and/or ``afterApplyUpdate``
     * methods, they'll be called before and after any updates are made,
     * respectively.
     *
     * Args:
     *     model (Backbone.Model):
     *         The model to update.
     *
     *     metadata (object):
     *         The metadata for the update.
     *
     *     html (string):
     *         The new HTML for the view.
     */
    _reloadFromUpdate(model, metadata, html) {
        this.trigger(`applyingUpdate:${metadata.type}`, metadata, html);

        if (model) {
            this.trigger(`applyingUpdate:${metadata.type}:${model.id}`,
                         metadata, html);

            if (_.isFunction(model.beforeApplyUpdate)) {
                model.beforeApplyUpdate(metadata);
            }

            if (metadata.modelData) {
                model.set(model.parse(_.extend({},
                                               model.attributes,
                                               metadata.modelData)));
            }

            this.trigger(`appliedModelUpdate:${metadata.type}:${model.id}`,
                         metadata, html);

            if (_.isFunction(model.afterApplyUpdate)) {
                model.afterApplyUpdate(metadata);
            }

            this.trigger(`appliedUpdate:${metadata.type}:${model.id}`,
                         metadata, html);
        }

        this.trigger(`appliedUpdate:${metadata.type}`, metadata, html);
    },
});
