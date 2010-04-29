RB = {};

RB.DiffComment = function(filediff, interfilediff, beginLineNum, endLineNum,
                          textOnServer) {
    this.filediff = filediff;
    this.interfilediff = interfilediff;
    this.beginLineNum = beginLineNum;
    this.endLineNum = endLineNum;
    this.text = textOnServer || "";
    this.saved = (textOnServer != undefined);

    return this;
}

$.extend(RB.DiffComment.prototype, {
    /*
     * Sets the current text in the comment block.
     *
     * @param {string} text  The new text to set.
     */
    setText: function(text) {
        this.text = text;
        $.event.trigger("textChanged", null, this);
    },

    /*
     * Returns the number of lines that this comment covers.
     *
     * @return {int} The number of lines this comment covers.
     */
    getNumLines: function() {
        return this.endLineNum - this.beginLineNum + 1;
    },

    /*
     * Saves the comment on the server.
     */
    save: function(options) {
        var self = this;
        options = options || {};

        rbApiCall({
            path: this._getURL(),
            data: {
                action: "set",
                num_lines: this.getNumLines(),
                text: this.text
            },
            success: function() {
                self.saved = true;
                $.event.trigger("saved", null, self);

                if ($.isFunction(options.success)) {
                    options.success();
                }
            }
        });
    },

    /*
     * Deletes the comment from the server.
     */
    deleteComment: function() {
        var self = this;

        if (this.saved) {
            rbApiCall({
                path: this._getURL(),
                data: {
                    action: "delete",
                    num_lines: this.getNumLines()
                },
                success: function() {
                    self.saved = false;
                    $.event.trigger("deleted", null, self);
                    self._deleteAndDestruct();
                }
            });
        } else {
            this._deleteAndDestruct();
        }
    },

    deleteIfEmpty: function() {
        if (this.text != "") {
            return;
        }

        this.deleteComment();
    },

    _deleteAndDestruct: function() {
        $.event.trigger("destroyed", null, this);
    },

    /*
     * Returns the URL used for API calls.
     *
     * @return {string} The URL used for API calls for this comment block.
     */
    _getURL: function() {
        var interfilediff_revision = null;
        var interfilediff_id = null;

        if (this.interfilediff != null) {
            interfilediff_revision = this.interfilediff['revision'];
            interfilediff_id = this.interfilediff['id'];
        }

        var filediff_revision = this.filediff['revision'];
        var filediff_id = this.filediff['id'];

        return "/reviewrequests/" + gReviewRequestId + "/diff/" +
               (interfilediff_revision == null
                    ? filediff_revision
                    : filediff_revision + "-" + interfilediff_revision) +
               "/file/" +
               (interfilediff_id == null
                    ? filediff_id
                    : filediff_id + "-" + interfilediff_id) +
               "/line/" + this.beginLineNum + "/comments/";
    }
});


RB.Diff = function(review_request, revision, interdiff_revision) {
    this.review_request = review_request;
    this.revision = revision;
    this.interdiff_revision = interdiff_revision;

    return this;
}

$.extend(RB.Diff.prototype, {
    getDiffFragment: function(fileid, filediff_id, revision,
                              interdiff_revision, chunk_index, onSuccess) {
        var revisionStr = revision;

        if (interdiff_revision != null) {
            revisionStr += "-" + interdiff_revision;
        }

        rbApiCall({
            url: SITE_ROOT + 'r/' + this.review_request.id + '/diff/' +
                 revisionStr + '/fragment/' + filediff_id +
                 '/chunk/' + chunk_index + '/',
            data: {},
            type: "GET",
            dataType: "html",
            complete: function(res, status) {
                if (status == "success") {
                    onSuccess(res.responseText);
                }
            }
        });
    },

    getDiffFile: function(filediff_id, filediff_revision,
                          interfilediff_id, interfilediff_revision,
                          file_index, onSuccess) {
        var revision_str = filediff_revision;

        if (interfilediff_id) {
            revision_str += "-" + interfilediff_revision;
        }

        $.ajax({
            type: "GET",
            url: SITE_ROOT + "r/" + this.review_request.id + "/diff/" +
                 revision_str + "/fragment/" + filediff_id +
                 "/?index=" + file_index + "&" + AJAX_SERIAL,
            complete: onSuccess
        });
    },

    getErrorString: function(rsp) {
        if (rsp.err.code == 207) {
            return 'The file "' + rsp.file + '" (revision ' + rsp.revision +
                    ') was not found in the repository';
        }

        return rsp.err.msg;
    },

    setForm: function(form) {
        this.form = form;
    },

    save: function(options) {
        var self = this;

        options = $.extend(true, {
            success: function() {},
            error: function() {}
        }, options);

        if (self.id != undefined) {
            options.error("The diff " + self.id + " was already created. " +
                          "This is a script error. Please report it.");
            return;
        }

        if (!self.form) {
            options.error("No data has been set for this diff. This " +
                          "is a script error. Please report it.");
            return;
        }

        self.review_request.ready(function() {
            rbApiCall({
                url: self.review_request.child_hrefs['diffs'],
                form: self.form,
                buttons: options.buttons,
                success: function(rsp) {
                    if (rsp.stat == "ok") {
                        options.success(rsp);
                    } else {
                        options.error(rsp, rsp.err.msg);
                    }
                }
            });
        });
    }
});


RB.ReviewRequest = function(id, path) {
    this.id = id;
    this.path = path;
    this.reviews = {};
    this.draft_review = null;
    this.child_hrefs = {};
    this.loaded = false;

    return this;
}

$.extend(RB.ReviewRequest, {
    /* Constants */
    CHECK_UPDATES_MSECS: 5 * 60 * 1000, // Every 5 minutes
    CLOSE_DISCARDED: 1,
    CLOSE_SUBMITTED: 2
});

$.extend(RB.ReviewRequest.prototype, {
    /* Review request API */
    createDiff: function(revision, interdiff_revision) {
        return new RB.Diff(this, revision, interdiff_revision);
    },

    createReview: function(review_id) {
        if (review_id == undefined) {
            if (this.draft_review == null) {
                this.draft_review = new RB.Review(this);
            }

            return this.draft_review;
        } else if (!this.reviews[review_id]) {
            this.reviews[review_id] = new RB.Review(this, review_id);
        }

        return this.reviews[review_id];
    },

    createScreenshot: function() {
        return new RB.Screenshot(this);
    },

    /*
     * Ensures that the review request's state is loaded.
     *
     * If it's not loaded, then a request will be made to load the state
     * before the callback is called.
     */
    ready: function(on_ready) {
        if (this.loaded) {
            on_ready();
        } else {
            var self = this;

            this._apiCall({
                type: "GET",
                path: "/",
                success: function(rsp) {
                    self.loaded = true;
                    self.child_hrefs = rsp.review_request.child_hrefs;
                    on_ready();
                }
            });
        }
    },

    setDraftField: function(options) {
        data = {}
        data[options.field] = options.value;

        this._apiCall({
            type: "PUT",
            path: "/draft/",
            buttons: options.buttons,
            data: data,
            success: options.success // XXX
        });
    },

    setStarred: function(starred) {
        var apiType;
        var path = "/users/" + gUserName + "/watched/review-requests/";
        var data = {};

        if (starred) {
            apiType = "POST";
            data['object_id'] = this.id;
        } else {
            apiType = "DELETE";
            path += this.id + "/";
        }

        rbApiCall({
            type: apiType,
            path: path,
            data: data,
            success: function() {}
        });
    },

    publish: function(options) {
        var self = this;

        options = $.extend(true, {}, options);

        self.ready(function() {
            self._apiCall({
                type: "PUT",
                url: self.child_hrefs['draft'],
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
                url: self.child_hrefs['draft'],
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

        self.ready(function() {
            self._apiCall({
                type: "PUT",
                path: "/",
                data: {
                    status: statusType
                },
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
                url: self.child_hrefs['last-update'],
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

        options.path = "/review-requests/" + this.id + options.path;

        if (!options.success) {
            options.success = function() { window.location = self.path; };
        }

        rbApiCall(options);
    }
});


RB.Review = function(review_request, id) {
    this.id = id;
    this.review_request = review_request;
    this.draft_reply = null;
    this.ship_it = null;
    this.body_top = null;
    this.body_bottom = null;
    this.url = null;
    this.loaded = false;

    return this;
}

$.extend(RB.Review.prototype, {
    createReply: function() {
        if (this.draft_reply == null) {
            this.draft_reply = new RB.ReviewReply(this);
        }

        return this.draft_reply;
    },

    ready: function(on_done) {
        if (this.loaded) {
            on_done();
        } else {
            this._load(on_done);
        }
    },

    ensureCreated: function(on_done) {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                on_done();
            } else {
                /* The review doesn't exist. Create it. */
                self.save({
                    success: function(rsp) {
                        self.id = rsp.review.id;
                        self.loaded = true;
                        on_done();
                    }
                });
            }
        });
    },

    save: function(options) {
        var data = {};

        if (this.ship_it != null) {
            data.ship_it = (this.ship_it ? 1 : 0);
        }

        if (this.body_top != null) {
            data.body_top = this.body_top;
        }

        if (this.body_bottom != null) {
            data.body_bottom = this.body_bottom;
        }

        if (options.public) {
            data.public = 1;
        }

        var self = this;

        this.ready(function() {
            var type;
            var url;

            if (self.loaded) {
                type = "PUT";
                url = self.url;
            } else {
                type = "POST";
                url = self.review_request.child_hrefs.reviews;
            }

            self._apiCall({
                type: type,
                url: url,
                data: data,
                buttons: options.buttons,
                success: function(rsp) {
                    self._loadDataFromResponse(rsp);

                    if ($.isFunction(options.success)) {
                        options.success(rsp);
                    }
                }
            });
        });
    },

    publish: function(options) {
        this.save($.extend(true, {
            public: true,
        }, options));
    },

    deleteReview: function(options) {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                self._apiCall({
                    type: "DELETE",
                    buttons: options.buttons,
                    success: options.success
                });
            } else if ($.isFunction(options.success)) {
                options.success();
            }
        });
    },

    _load: function(on_done) {
        var self = this;

        self.review_request.ready(function() {
            rbApiCall({
                type: "GET",
                url: self.review_request.child_hrefs.reviews + "draft/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done();
                },
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.review.id;
        this.ship_it = rsp.review.ship_it;
        this.body_top = rsp.review.body_top;
        this.body_bottom = rsp.review.body_bottom;
        this.child_hrefs = rsp.review.child_hrefs;
        this.url = rsp.review.href;
        this.loaded = true;
    },

    _apiCall: function(options) {
        var self = this;

        self.review_request.ready(function() {
            if (!options.url) {
                options.url = self.review_request.child_hrefs.reviews +
                              self.id + "/" + (options.path || "");
            }

            if (!options.success) {
                options.success = function() {
                    window.location = self.review_request.path;
                };
            }

            rbApiCall(options);
        });
    }
});


RB.ReviewGroup = function(id) {
    this.id = id;

    return this;
}

$.extend(RB.ReviewGroup.prototype, {
    setStarred: function(starred) {
        rbApiCall({
            path: "/groups/" + this.id + (starred ? "/star/" : "/unstar/"),
            success: function() {}
        });
    }
});


RB.ReviewReply = function(review) {
    this.review = review;

    return this;
}

$.extend(RB.ReviewReply.prototype, {
    addComment: function(options) {
        rbApiCall({
            path: "/reviewrequests/" + this.review.review_request.id +
                  "/reviews/" + this.review.id + "/replies/draft/",
            data: {
                value:     options.text,
                id:        options.context_id,
                type:      options.context_type,
                review_id: this.review.id
            },
            buttons: options.buttons,
            success: options.success
        });
    },

    publish: function(options) {
        rbApiCall({
            path: '/reviewrequests/' + this.review.review_request.id +
                  '/reviews/' + this.review.id + '/replies/draft/save/',
            buttons: options.buttons,
            errorText: "Saving the reply draft has " +
                       "failed due to a server error:",
            success: options.success
        });
    },

    discard: function(options) {
        rbApiCall({
            path: '/reviewrequests/' + this.review.review_request.id +
                  '/reviews/' + this.review.id + '/replies/draft/discard/',
            buttons: options.buttons,
            errorText: "Discarding the reply draft " +
                       "has failed due to a server error:",
            success: options.success
        });
    }
});


RB.Screenshot = function(review_request, id) {
    this.review_request = review_request;
    this.id = id;

    return this;
}

$.extend(RB.Screenshot.prototype, {
    setFile: function(file) {
        this.file = file;
    },

    setForm: function(form) {
        this.form = form;
    },

    save: function(options) {
        options = $.extend(true, {
            success: function() {},
            error: function() {}
        }, options);

        if (this.id != undefined) {
            /* TODO: Support updating screenshots eventually. */
            options.error("The screenshot " + this.id + " was already " +
                          "created. This is a script error. Please " +
                          "report it.");
            return;
        }

        if (this.form) {
            this._saveForm(options);
        } else if (this.file) {
            this._saveFile(options);
        } else {
            options.error("No data has been set for this screenshot. This " +
                          "is a script error. Please report it.");
            return;
        }
    },

    _saveForm: function(options) {
        this._saveApiCall(options.success, options.error, {
            path: 'new/',
            buttons: options.buttons,
            form: this.form
        });
    },

    _saveFile: function(options) {
        var boundary = "-----multipartformboundary" + new Date().getTime();
        var blob = "";
        blob += "--" + boundary + "\r\n";
        blob += 'Content-Disposition: form-data; name="path"; ' +
                           'filename="' + this.file.name + '"\r\n';
        blob += 'Content-Type: application/octet-stream\r\n';
        blob += '\r\n';
        blob += this.file.getAsBinary();
        blob += '\r\n';
        blob += "--" + boundary + "--\r\n";
        blob += '\r\n';

        this._saveApiCall(options.success, options.error, {
            path: 'new/',
            buttons: options.buttons,
            data: blob,
            processData: false,
            contentType: "multipart/form-data; boundary=" + boundary,
            xhr: function() {
                var xhr = $.ajaxSettings.xhr()
                xhr.send = function(data) {
                    xhr.sendAsBinary(blob);
                };

                return xhr;
            }
        });
    },

    _saveApiCall: function(onSuccess, onError, options) {
        rbApiCall($.extend(options, {
            path: '/reviewrequests/' + this.review_request.id +
                  '/screenshot/' + options.path,
            success: function(rsp) {
                if (rsp.stat == "ok") {
                    if ($.isFunction(onSuccess)) {
                        onSuccess(rsp, rsp.screenshot);
                    }
                } else if ($.isFunction(onError)) {
                    onError(rsp, rsp.err.msg);
                }
            }
        }));
    }
});


RB.ScreenshotComment = function(screenshot_id, x, y, width, height,
                                textOnServer) {
    this.screenshot_id = screenshot_id;
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.text = textOnServer || "";
    this.saved = (textOnServer != undefined);

    return this;
}

$.extend(RB.ScreenshotComment.prototype, {
    /*
     * Sets the current text in the comment block.
     *
     * @param {string} text  The new text to set.
     */
    setText: function(text) {
        this.text = text;
        $.event.trigger("textChanged", null, this);
    },

    /*
     * Saves the comment on the server.
     */
    save: function(options) {
        options = $.extend({
            success: function() {}
        }, options);

        var self = this;

        rbApiCall({
            path: this._getURL(),
            data: {
                action: "set",
                text: this.text
            },
            success: function() {
                self.saved = true;
                $.event.trigger("saved", null, self);
                options.success();
            }
        });
    },

    /*
     * Deletes the comment from the server.
     */
    deleteComment: function() {
        var self = this;

        if (this.saved) {
            rbApiCall({
                path: this._getURL(),
                data: {
                    action: "delete"
                },
                success: function() {
                    self.saved = false;
                    $.event.trigger("deleted", null, self);
                    self._deleteAndDestruct();
                }
            });
        } else {
            this._deleteAndDestruct();
        }
    },

    deleteIfEmpty: function() {
        if (this.text != "") {
            return;
        }

        this.deleteComment();
    },

    _deleteAndDestruct: function() {
        $.event.trigger("destroyed", null, this);
    },

    /*
     * Returns the URL used for API calls.
     *
     * @return {string} The URL used for API calls for this comment block.
     */
    _getURL: function() {
        return "/reviewrequests/" + gReviewRequestId + "/s/" +
               this.screenshot_id + "/comments/" +
               Math.round(this.width) + "x" + Math.round(this.height) +
               "+" + Math.round(this.x) + "+" + Math.round(this.y) + "/";
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
function rbApiCall(options) {
    var url = options.url || (SITE_ROOT + "api" + options.path);

    function doCall() {
        if (options.buttons) {
            options.buttons.attr("disabled", true);
        }

        var activityIndicator = $("#activity-indicator");

        if (!options.noActivityIndicator) {
            activityIndicator
                .removeClass("error")
                .text((options.type || options.type == "GET")
                      ? "Loading..." : "Saving...")
                .show();
        }

        var data = $.extend(true, {
            url: url,
            data: options.data || {dummy: ""},
            dataType: options.dataType || "json",
            error: function(xhr, textStatus, errorThrown) {
                var rsp = null;

                try {
                    rsp = $.httpData(xhr, options.dataType || "json");
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

            if (!options.noActivityIndicator &&
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
            .bind("resize", function() {
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

    if (options.type != "GET") {
        $.funcQueue("rbapicall").add(doCall);
        $.funcQueue("rbapicall").start();
    } else {
        doCall();
    }
}


// vim: set et:sw=4:
