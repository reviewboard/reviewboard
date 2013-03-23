RB.ReviewRequest = function(id, prefix, path) {
    this.id = id;
    this.prefix = prefix;
    this.path = path;
    this.reviews = {};
    this.draft_review = null;
    this.links = {};
    this.loaded = false;

    return this;
};

$.extend(RB.ReviewRequest, {
    /* Constants */
    CHECK_UPDATES_MSECS: 5 * 60 * 1000, // Every 5 minutes
    CLOSE_DISCARDED: 1,
    CLOSE_SUBMITTED: 2
});

$.extend(RB.ReviewRequest.prototype, {
    /* Review request API */
    createDiff: function(revision, interdiff_revision) {
        return new RB.Diff({
            parentObject: this
        });
    },

    createReview: function(review_id) {
        if (review_id == undefined) {
            if (this.draft_review == null) {
                this.draft_review = new RB.DraftReview({
                    parentObject: this
                });
            }

            return this.draft_review;
        } else if (!this.reviews[review_id]) {
            this.reviews[review_id] = new RB.Review({
                parentObject: this,
                id: review_id
            });
        }

        return this.reviews[review_id];
    },

    createScreenshot: function(screenshot_id) {
        return new RB.Screenshot({
            parentObject: this,
            id: screenshot_id
        });
    },

    createFileAttachment: function(file_attachment_id) {
        return new RB.FileAttachment({
            parentObject: this,
            id: file_attachment_id
        });
    },

    /*
     * Ensures that the review request's state is loaded.
     *
     * If it's not loaded, then a request will be made to load the state
     * before the callback is called.
     */
    ready: function(on_ready) {
        if (this.loaded) {
            on_ready.apply(this, arguments);
        } else {
            var self = this;

            this._apiCall({
                type: "GET",
                path: "/",
                success: function(rsp) {
                    self.loaded = true;
                    self.links = rsp.review_request.links;
                    on_ready.apply(this, arguments);
                }
            });
        }
    },

    // XXX Needed until we move this to Backbone.js.
    ensureCreated: function(cb) {
        this.ready(cb);
    },

    setDraftField: function(options) {
        data = {};
        data[options.field] = options.value;

        if (options.field == "target_people" ||
            options.field == "target_groups") {
            data.expand = options.field;
        }

        this._apiCall({
            type: "PUT",
            path: "/draft/",
            buttons: options.buttons,
            data: data,
            success: options.success // XXX
        });
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

    publish: function(options) {
        var self = this;

        options = $.extend(true, {}, options);

        self.ready(function() {
            self._apiCall({
                type: "PUT",
                url: self.links.draft.href,
                data: {
                    public: 1
                },
                buttons: options.buttons
            });
        });
    },

    discardDraft: function(options) {
        var self = this;

        self.ready(function() {
            self._apiCall({
                type: "DELETE",
                url: self.links.draft.href,
                buttons: options.buttons
            });
        });
    },

    close: function(options) {
        var self = this;
        var statusType;

        if (options.type == RB.ReviewRequest.CLOSE_DISCARDED) {
            statusType = "discarded";
        } else if (options.type == RB.ReviewRequest.CLOSE_SUBMITTED) {
            statusType = "submitted";
        } else {
            return;
        }

        data = {
            status: statusType
        };

        if (options.description !== undefined) {
            data.description = options.description;
        }

        self.ready(function() {
            self._apiCall({
                type: "PUT",
                path: "/",
                data: data,
                buttons: options.buttons
            });
        });
    },

    reopen: function(options) {
        options = $.extend(true, {}, options);

        this._apiCall({
            type: "PUT",
            path: "/",
            data: {
                status: "pending"
            },
            buttons: options.buttons
        });
    },

    deletePermanently: function(options) {
        options = $.extend(true, {}, options);

        this._apiCall({
            type: "DELETE",
            path: "/",
            buttons: options.buttons,
            success: options.success
        });
    },

    markUpdated: function(timestamp) {
        this.lastUpdateTimestamp = timestamp;
    },

    beginCheckForUpdates: function(type, lastUpdateTimestamp) {
        var self = this;

        this.checkUpdatesType = type;
        this.lastUpdateTimestamp = lastUpdateTimestamp;

        setTimeout(function() { self._checkForUpdates(); },
                   RB.ReviewRequest.CHECK_UPDATES_MSECS);
    },

    _checkForUpdates: function() {
        var self = this;

        self.ready(function() {
            self._apiCall({
                type: "GET",
                noActivityIndicator: true,
                url: self.links.last_update.href,
                success: function(rsp) {
                    var last_update = rsp.last_update;

                    if ((self.checkUpdatesType == undefined ||
                         self.checkUpdatesType == last_update.type) &&
                        self.lastUpdateTimestamp != last_update.timestamp) {
                        $.event.trigger("updated", [last_update], self);
                    }

                    self.lastUpdateTimestamp = last_update.timestamp;

                    setTimeout(function() { self._checkForUpdates(); },
                               RB.ReviewRequest.CHECK_UPDATES_MSECS);
                }
            });
        });
    },

    _apiCall: function(options) {
        var self = this;

        options.prefix = this.prefix;
        options.path = "/review-requests/" + this.id + options.path;

        if (!options.success) {
            options.success = function() { window.location = self.path; };
        }

        RB.apiCall(options);
    }
});


/*
 * Convenience wrapper for Review Board API functions. This will handle
 * any button disabling/enabling, write to the correct path prefix, form
 * uploading, and displaying server errors.
 *
 * options has the following fields:
 *
 *    buttons  - An optional list of buttons to disable/enable.
 *    form     - A form to upload, if any.
 *    type     - The request type (defaults to "POST").
 *    prefix   - The prefix to put on the API path (after SITE_ROOT, before
 *               "api")
 *    path     - The relative path to the Review Board API tree.
 *    data     - Data to send with the request.
 *    success  - An optional success callback. The default one will reload
 *               the page.
 *    error    - An optional error callback, called after the error banner
 *               is displayed.
 *    complete - An optional complete callback, called after the success or
 *               error callbacks.
 *
 * @param {object} options  The options, listed above.
 */
RB.apiCall = function(options) {
    var prefix = options.prefix || "";
    var url = options.url || (SITE_ROOT + prefix + "api" + options.path);

    function doCall() {
        if (options.buttons) {
            options.buttons.attr("disabled", true);
        }

        var activityIndicator = $("#activity-indicator");

        if (RB.ajaxOptions.enableIndicator && !options.noActivityIndicator) {
            activityIndicator
                .removeClass("error")
                .text((options.type || options.type == "GET")
                      ? "Loading..." : "Saving...")
                .show();
        }

        var data = $.extend(true, {
            url: url,
            data: options.data,
            dataType: options.dataType || "json",
            error: function(xhr, textStatus, errorThrown) {
                var rsp = null;

                try {
                    rsp = $.parseJSON(xhr.responseText);
                } catch (e) {
                }

                if ((rsp && rsp.stat) || xhr.status == 204) {
                    if ($.isFunction(options.success)) {
                        options.success(rsp, xhr.status);
                    }

                    return;
                }

                var responseText = xhr.responseText;
                activityIndicator
                    .addClass("error")
                    .text("A server error occurred.")
                    .append(
                        $("<a/>")
                            .text("Show Details")
                            .attr("href", "#")
                            .click(function() {
                                showErrorPage(xhr, responseText);
                            })
                    )
                    .append(
                        $("<a/>")
                            .text("Dismiss")
                            .attr("href", "#")
                            .click(function() {
                                activityIndicator.fadeOut("fast");
                                return false;
                            })
                    );

                if ($.isFunction(options.error)) {
                    options.error(xhr, textStatus, errorThrown);
                }
            }
        }, options);

        data.complete = function(xhr, status) {
            if (options.buttons) {
                options.buttons.attr("disabled", false);
            }

            if (RB.ajaxOptions.enableIndicator &&
                !options.noActivityIndicator &&
                !activityIndicator.hasClass("error")) {
                activityIndicator
                    .delay(1000)
                    .fadeOut("fast");
            }

            if ($.isFunction(options.complete)) {
                options.complete(xhr, status);
            }

            $.funcQueue("rbapicall").next();
        };

        if (data.data == null || data.data == undefined ||
            typeof data.data == "object") {
            data.data = $.extend({
                api_format: 'json'
            }, data.data || {});
        }

        if (options.form) {
            options.form.ajaxSubmit(data);
        } else {
            $.ajax(data);
        }
    }

    function showErrorPage(xhr, data) {
        var iframe = $('<iframe/>')
            .width("100%");

        var requestData = "(none)";

        if (options.data) {
            requestData = $.param(options.data);
        }

        var errorBox = $('<div class="server-error-box"/>')
            .appendTo("body")
            .append('<p><b>Error Code:</b> ' + xhr.status + '</p>')
            .append('<p><b>Error Text:</b> ' + xhr.statusText + '</p>')
            .append('<p><b>Request URL:</b> ' + url + '</p>')
            .append('<p><b>Request Data:</b> ' + requestData + '</p>')
            .append('<p class="response-data"><b>Response Data:</b></p>')
            .append(
                '<p>There may be useful error details below. The following ' +
                'error page may be useful to your system administrator or ' +
                'when <a href="http://www.reviewboard.org/bugs/new/">' +
                'reporting a bug</a>. To save the page, right-click the ' +
                'error below and choose "Save Page As," if available, ' +
                'or "View Source" and save the result as a ' +
                '<tt>.html</tt> file.</p>')
            .append('<p><b>Warning:</b> Be sure to remove any sensitive ' +
                    'material that may exist in the error page before ' +
                    'reporting a bug!</p>')
            .append(iframe)
            .on("resize", function() {
                iframe.height($(this).height() - iframe.position().top);
            })
            .modalBox({
                stretchX: true,
                stretchY: true,
                title: "Server Error Details"
            });

        var doc = iframe[0].contentDocument ||
                  iframe[0].contentWindow.document;
        doc.open();
        doc.write(data);
        doc.close();
    }

    options.type = options.type || "POST";

    /* We allow disabling the function queue for the sake of unit tests. */
    if (RB.ajaxOptions.enableQueuing && options.type !== "GET") {
        $.funcQueue("rbapicall").add(doCall);
        $.funcQueue("rbapicall").start();
    } else {
        doCall();
    }
};

RB.ajaxOptions = {
    enableQueuing: true,
    enableIndicator: true
};

/*
 * Call RB.apiCall instead of $.ajax.
 *
 * We wrap instead of assign for now so that we can hook in/override
 * RB.apiCall with unit tests.
 */
Backbone.ajax = function(options) {
    return RB.apiCall(options);
};


if (!XMLHttpRequest.prototype.sendAsBinary) {
    XMLHttpRequest.prototype.sendAsBinary = function(datastr) {
        var data = new Uint8Array(
            Array.prototype.map.call(datastr, function(x) {
                return x.charCodeAt(0) & 0xFF;
            }));

        XMLHttpRequest.prototype.send.call(this, data.buffer);
    };
}


// vim: set et:sw=4:
