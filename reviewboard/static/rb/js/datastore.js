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
