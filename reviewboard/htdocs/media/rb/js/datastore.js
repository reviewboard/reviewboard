RB = {};

RB.DiffComment = function(review, id, filediff, interfilediff, beginLineNum,
                          endLineNum) {
    this.id = id;
    this.review = review;
    this.filediff = filediff;
    this.interfilediff = interfilediff;
    this.beginLineNum = beginLineNum;
    this.endLineNum = endLineNum;
    this.text = "";
    this.loaded = false;
    this.url = null;

    return this;
}

$.extend(RB.DiffComment.prototype, {
    ready: function(on_ready) {
        if (this.loaded) {
            on_ready.apply(this, arguments);
        } else {
            this._load(on_ready);
        }
    },

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

        self.ready(function() {
            self.review.ensureCreated(function() {
                var type;
                var url;
                var data = {
                    text: self.text,
                    first_line: self.beginLineNum,
                    num_lines: self.getNumLines()
                };

                if (self.loaded) {
                    type = "PUT";
                    url = self.url;
                } else {
                    data.filediff_id = self.filediff.id;
                    url = self.review.links.diff_comments.href;

                    if (self.interfilediff) {
                        data.interfilediff_id = self.interfilediff_id;
                    }
                }

                rbApiCall({
                    type: type,
                    url: url,
                    data: data,
                    success: function(rsp) {
                        self._loadDataFromResponse(rsp);

                        $.event.trigger("saved", null, self);

                        if ($.isFunction(options.success)) {
                            options.success();
                        }
                    }
                });
            });
        });
    },

    /*
     * Deletes the comment from the server.
     */
    deleteComment: function() {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                rbApiCall({
                    type: "DELETE",
                    url: self.url,
                    success: function() {
                        $.event.trigger("deleted", null, self);
                        self._deleteAndDestruct();
                    }
                });
            } else {
                self._deleteAndDestruct();
            }
        });
    },

    deleteIfEmpty: function() {
        if (this.text == "") {
            this.deleteComment();
        }
    },

    _deleteAndDestruct: function() {
        $.event.trigger("destroyed", null, this);
    },

    _load: function(on_done) {
        var self = this;

        if (!self.id) {
            on_done.apply(this, arguments);
            return;
        }

        self.review.ready(function() {
            if (!self.review.loaded) {
                on_done.apply(this, arguments);
                return;
            }

            rbApiCall({
                type: "GET",
                url: self.review.links.diff_comments.href + self.id + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                },
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.diff_comment.id;
        this.text = rsp.diff_comment.text;
        this.beginLineNum = rsp.diff_comment.first_line;
        this.endLineNum = rsp.diff_comment.num_lines + this.beginLineNum;
        this.links = rsp.diff_comment.links;
        this.url = rsp.diff_comment.links.self.href;
        this.loaded = true;
    }
});


RB.DiffCommentReply = function(reply, id, reply_to_id) {
    this.id = id;
    this.reply = reply;
    this.text = "";
    this.reply_to_id = reply_to_id;
    this.loaded = false;
    this.url = null;

    return this;
}

$.extend(RB.DiffCommentReply.prototype, {
    ready: function(on_ready) {
        if (this.loaded) {
            on_ready.apply(this, arguments);
        } else {
            this._load(on_ready);
        }
    },

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
        var self = this;
        options = options || {};

        self.ready(function() {
            self.reply.ensureCreated(function() {
                var type;
                var url;
                var data = {
                    text: self.text
                };

                if (self.loaded) {
                    type = "PUT";
                    url = self.url;
                } else {
                    data.reply_to_id = self.reply_to_id;
                    url = self.reply.links.diff_comments.href;
                }

                rbApiCall({
                    type: type,
                    url: url,
                    data: data,
                    success: function(rsp) {
                        self._loadDataFromResponse(rsp);

                        $.event.trigger("saved", null, self);

                        if ($.isFunction(options.success)) {
                            options.success();
                        }
                    }
                });
            });
        });
    },

    /*
     * Deletes the comment from the server.
     */
    deleteComment: function() {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                rbApiCall({
                    type: "DELETE",
                    url: self.url,
                    success: function() {
                        $.event.trigger("deleted", null, self);
                        self._deleteAndDestruct();
                    }
                });
            } else {
                self._deleteAndDestruct();
            }
        });
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

    _load: function(on_done) {
        var self = this;

        if (!self.id) {
            on_done.apply(this, arguments);
            return;
        }

        self.reply.ready(function() {
            if (!self.reply.loaded) {
                on_done.apply(this, arguments);
                return;
            }

            rbApiCall({
                type: "GET",
                url: self.reply.links.diff_comments.href + self.id + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                },
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.diff_comment.id;
        this.text = rsp.diff_comment.text;
        this.links = rsp.diff_comment.links;
        this.url = rsp.diff_comment.links.self.href;
        this.loaded = true;
    }
});


RB.Diff = function(review_request, revision, interdiff_revision) {
    this.review_request = review_request;
    this.revision = revision;
    this.interdiff_revision = interdiff_revision;

    return this;
}

$.extend(RB.Diff.prototype, {
    getDiffFragment: function(review_base_url, fileid, filediff_id, revision,
                              interdiff_revision, chunk_index, onSuccess) {
        var revisionStr = revision;

        if (interdiff_revision != null) {
            revisionStr += "-" + interdiff_revision;
        }

        rbApiCall({
            url: review_base_url + 'diff/' + revisionStr + '/fragment/' +
                 filediff_id + '/chunk/' + chunk_index + '/',
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

    getDiffFile: function(review_base_url, filediff_id, filediff_revision,
                          interfilediff_id, interfilediff_revision,
                          file_index, onSuccess) {
        var revision_str = filediff_revision;

        if (interfilediff_id) {
            revision_str += "-" + interfilediff_revision;
        }

        $.ajax({
            type: "GET",
            url: review_base_url + "diff/" + revision_str + "/fragment/" +
                 filediff_id + "/?index=" + file_index + "&" + AJAX_SERIAL,
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
                url: self.review_request.links.diffs.href,
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


RB.ReviewRequest = function(id, prefix, path) {
    this.id = id;
    this.prefix = prefix;
    this.path = path;
    this.reviews = {};
    this.draft_review = null;
    this.links = {};
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

    createScreenshot: function(screenshot_id) {
        return new RB.Screenshot(this, screenshot_id);
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
    createDiffComment: function(id, filediff, interfilediff, beginLineNum,
                                endLineNum) {
        return new RB.DiffComment(this, id, filediff, interfilediff,
                                  beginLineNum, endLineNum);
    },

    createScreenshotComment: function(id, screenshot_id, x, y, width, height) {
        return new RB.ScreenshotComment(this, id, screenshot_id, x, y,
                                        width, height);
    },

    createReply: function() {
        if (this.draft_reply == null) {
            this.draft_reply = new RB.ReviewReply(this);
        }

        return this.draft_reply;
    },

    ready: function(on_done) {
        if (this.loaded) {
            on_done.apply(this, arguments);
        } else {
            this._load(on_done);
        }
    },

    ensureCreated: function(on_done) {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                on_done.apply(this, arguments);
            } else {
                /* The review doesn't exist. Create it. */
                self.save({
                    success: function(rsp) {
                        self.id = rsp.review.id;
                        self.loaded = true;
                        on_done.apply(this, arguments);
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
                url = self.review_request.links.reviews.href;
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
                url: self.review_request.links.reviews.href +
                     (self.id || "draft") + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                }
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.review.id;
        this.ship_it = rsp.review.ship_it;
        this.body_top = rsp.review.body_top;
        this.body_bottom = rsp.review.body_bottom;
        this.links = rsp.review.links;
        this.url = rsp.review.links.self.href;
        this.loaded = true;
    },

    _apiCall: function(options) {
        var self = this;

        self.review_request.ready(function() {
            if (!options.url) {
                options.url = self.review_request.links.reviews.href +
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
        var apiType;
        var path = "/users/" + gUserName + "/watched/review-groups/";
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
    }
});


RB.ReviewReply = function(review, id) {
    this.review = review;
    this.id = id;
    this.body_top = null;
    this.body_bottom = null;
    this.url = null;
    this.loaded = false;

    return this;
}

$.extend(RB.ReviewReply.prototype, {
    ready: function(on_done) {
        if (this.loaded) {
            on_done.apply(this, arguments);
        } else {
            this._load(on_done);
        }
    },

    ensureCreated: function(on_done) {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                on_done.apply(this, arguments);
            } else {
                /* The review doesn't exist. Create it. */
                self.save({
                    success: function(rsp) {
                        self._loadDataFromResponse(rsp);
                        on_done.apply(this, arguments);
                    }
                });
            }
        });
    },

    save: function(options) {
        var data = {};

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
                url = self.review.links.replies.href;
            }

            rbApiCall({
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
            errorText: "Saving the reply draft has " +
                       "failed due to a server error:",
        }, options));
    },

    discard: function(options) {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                rbApiCall($.extend(true, options, {
                    url: self.url,
                    type: "DELETE",
                    errorText: "Discarding the reply draft " +
                               "has failed due to a server error:",
                }));
            } else if ($.isFunction(options.success)) {
                options.success();
            }
        });
    },

    discardIfEmpty: function(options) {
        var self = this;

        self.ready(function() {
            if (self.body_top || self.body_bottom) {
                return;
            }

            /* We can only discard if there are on comments of any kind. */
            rbApiCall({
                type: "GET",
                url: self.links.diff_comments.href,
                success: function(rsp, status) {
                    if (rsp.diff_comments.length == 0) {
                        rbApiCall({
                            type: "GET",
                            url: self.links.screenshot_comments.href,
                            success: function(rsp, status) {
                                if (rsp.screenshot_comments.length == 0) {
                                    self.discard(options);
                                }
                            }
                        });
                    }
                }
            });
        });
    },

    _load: function(on_done) {
        var self = this;

        self.review.ready(function() {
            rbApiCall({
                type: "GET",
                url: self.review.links.replies.href +
                     (self.id ? self.id : "draft") + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                },
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.reply.id;
        this.body_top = rsp.reply.body_top;
        this.body_bottom = rsp.reply.body_bottom;
        this.links = rsp.reply.links;
        this.url = rsp.reply.links.self.href;
        this.loaded = true;
    }
});


RB.Screenshot = function(review_request, id) {
    this.review_request = review_request;
    this.id = id;
    this.caption = null;
    this.thumbnail_url = null;
    this.path = null;
    this.url = null;
    this.loaded = false;

    return this;
}

$.extend(RB.Screenshot.prototype, {
    setFile: function(file) {
        this.file = file;
    },

    setForm: function(form) {
        this.form = form;
    },

    ready: function(on_done) {
        if (this.loaded && this.id) {
            on_done.apply(this, arguments);
        } else {
            this._load(on_done);
        }
    },

    save: function(options) {
        options = $.extend(true, {
            success: function() {},
            error: function() {}
        }, options);

        if (this.id) {
            var data = {};

            if (this.caption != null) {
                data.caption = this.caption;
            }

            var self = this;

            this.ready(function() {
                rbApiCall({
                    type: "PUT",
                    url: self.url,
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
        } else {
            if (this.form) {
                this._saveForm(options);
            } else if (this.file) {
                this._saveFile(options);
            } else {
                options.error("No data has been set for this screenshot. " +
                              "This is a script error. Please report it.");
            }
        }
    },

    deleteScreenshot: function() {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                rbApiCall({
                    type: "DELETE",
                    url: self.url,
                    success: function() {
                        $.event.trigger("deleted", null, self);
                        self._deleteAndDestruct();
                    }
                });
            }
        });
    },

    _load: function(on_done) {
        if (!this.id) {
            on_done.apply(this, arguments);
            return;
        }

        var self = this;

        self.review_request.ready(function() {
            rbApiCall({
                type: "GET",
                url: self.review_request.links.screenshots.href + self.id + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                }
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.screenshot.id;
        this.caption = rsp.screenshot.caption;
        this.thumbnail_url = rsp.screenshot.thumbnail_url;
        this.path = rsp.screenshot.path;
        this.url = rsp.screenshot.links.self.href;
        this.loaded = true;
    },

    _saveForm: function(options) {
        this._saveApiCall(options.success, options.error, {
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
        var self = this;

        self.review_request.ready(function() {
            rbApiCall($.extend(options, {
                url: self.review_request.links.screenshots.href,
                success: function(rsp) {
                    if (rsp.stat == "ok") {
                        self._loadDataFromResponse(rsp);

                        if ($.isFunction(onSuccess)) {
                            onSuccess(rsp, rsp.screenshot);
                        }
                    } else if ($.isFunction(onError)) {
                        onError(rsp, rsp.err.msg);
                    }
                }
            }));
        });
    },

    _deleteAndDestruct: function() {
        $.event.trigger("destroyed", null, this);
    }
});


RB.ScreenshotComment = function(review, id, screenshot_id, x, y, width,
                                height) {
    this.id = id;
    this.review = review;
    this.screenshot_id = screenshot_id;
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.text = "";
    this.loaded = false;
    this.url = null;

    return this;
}

$.extend(RB.ScreenshotComment.prototype, {
    ready: function(on_ready) {
        if (this.loaded) {
            on_ready.apply(this, arguments);
        } else {
            this._load(on_ready);
        }
    },

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
        var self = this;

        options = $.extend({
            success: function() {}
        }, options);

        self.ready(function() {
            self.review.ensureCreated(function() {
                var type;
                var url;
                var data = {
                    text: self.text,
                    x: self.x,
                    y: self.y,
                    w: self.width,
                    h: self.height
                };

                if (self.loaded) {
                    type = "PUT";
                    url = self.url;
                } else {
                    data.screenshot_id = self.screenshot_id;
                    url = self.review.links.screenshot_comments.href;
                }

                rbApiCall({
                    type: type,
                    url: url,
                    data: data,
                    success: function(rsp) {
                        self._loadDataFromResponse(rsp);
                        $.event.trigger("saved", null, self);
                        options.success();
                    }
                });
            });
        });
    },

    /*
     * Deletes the comment from the server.
     */
    deleteComment: function() {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                rbApiCall({
                    type: "DELETE",
                    url: self.url,
                    success: function() {
                        $.event.trigger("deleted", null, self);
                        self._deleteAndDestruct();
                    }
                });
            } else {
                this._deleteAndDestruct();
            }
        });
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

    _load: function(on_done) {
        var self = this;

        if (!self.id) {
            on_done.apply(this, arguments);
            return;
        }

        self.review.ready(function() {
            if (!self.review.loaded) {
                on_done.apply(this, arguments);
                return;
            }

            rbApiCall({
                type: "GET",
                url: self.review.links.screenshot_comments.href +
                     self.id + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                },
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.screenshot_comment.id;
        this.text = rsp.screenshot_comment.text;
        this.x = rsp.screenshot_comment.x;
        this.y = rsp.screenshot_comment.y;
        this.width = rsp.screenshot_comment.w;
        this.height = rsp.screenshot_comment.h;
        this.links = rsp.screenshot_comment.links;
        this.url = rsp.screenshot_comment.links.self.href;
        this.loaded = true;
    }
});


RB.ScreenshotCommentReply = function(reply, id, reply_to_id) {
    this.id = id;
    this.reply = reply;
    this.text = "";
    this.reply_to_id = reply_to_id;
    this.loaded = false;
    this.url = null;

    return this;
}

$.extend(RB.ScreenshotCommentReply.prototype, {
    ready: function(on_ready) {
        if (this.loaded) {
            on_ready.apply(this, arguments);
        } else {
            this._load(on_ready);
        }
    },

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
        var self = this;
        options = options || {};

        self.ready(function() {
            self.reply.ensureCreated(function() {
                var type;
                var url;
                var data = {
                    text: self.text
                };

                if (self.loaded) {
                    type = "PUT";
                    url = self.url;
                } else {
                    data.reply_to_id = self.reply_to_id;
                    url = self.reply.links.screenshot_comments.href;
                }

                rbApiCall({
                    type: type,
                    url: url,
                    data: data,
                    success: function(rsp) {
                        self._loadDataFromResponse(rsp);

                        $.event.trigger("saved", null, self);

                        if ($.isFunction(options.success)) {
                            options.success();
                        }
                    }
                });
            });
        });
    },

    /*
     * Deletes the comment from the server.
     */
    deleteComment: function() {
        var self = this;

        self.ready(function() {
            if (self.loaded) {
                rbApiCall({
                    type: "DELETE",
                    url: self.url,
                    success: function() {
                        $.event.trigger("deleted", null, self);
                        self._deleteAndDestruct();
                    }
                });
            } else {
                self._deleteAndDestruct();
            }
        });
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

    _load: function(on_done) {
        var self = this;

        if (!self.id) {
            on_done.apply(this, arguments);
            return;
        }

        self.reply.ready(function() {
            if (!self.reply.loaded) {
                on_done.apply(this, arguments);
                return;
            }

            rbApiCall({
                type: "GET",
                url: self.reply.links.screenshot_comments.href + self.id + "/",
                success: function(rsp, status) {
                    if (status != 404) {
                        self._loadDataFromResponse(rsp);
                    }

                    on_done.apply(this, arguments);
                },
            });
        });
    },

    _loadDataFromResponse: function(rsp) {
        this.id = rsp.screenshot_comment.id;
        this.text = rsp.screenshot_comment.text;
        this.links = rsp.screenshot_comment.links;
        this.url = rsp.screenshot_comment.links.self.href;
        this.loaded = true;
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
function rbApiCall(options) {
    var prefix = options.prefix || "";
    var url = options.url || (SITE_ROOT + prefix + "api" + options.path);

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
            data: options.data,
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

        if (typeof data.data == "object") {
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
