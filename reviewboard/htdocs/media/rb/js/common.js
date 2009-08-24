/*
 * Shows an error banner with the specified text and error data.
 *
 * @param {string} text  The error text.
 * @param {string} data  The detailed error output from the server.
 */
function showError(text, data) {
    var banner = $('<div class="banner"/>')
        .appendTo($("#error"))
        .append("<p><h1>Error:</h1> " + text + "</p>");

    $('<input type="submit" value="Dismiss"/>')
        .appendTo(banner)
        .click(function() {
            banner.remove();
        });

    $('<input type="submit" value="Details"/>')
        .appendTo(banner)
        .click(function() {
            var iframe = $('<iframe/>')
                .width("100%");

            var errorBox = $('<div class="server-error-box"/>')
                .appendTo("body")
                .append(
                    '<p>The following error page should be saved and ' +
                    'attached when contacting your system administrator or ' +
                    '<a href="http://www.review-board.org/bugs/new/">' +
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
        });
}


/*
 * Shows an error banner with some default error text.
 *
 * @param {string} specific  The specific error text.
 * @param {string} data      The detailed error output from the server.
 */
function showServerError(specific, data) {
    showError(specific +
              "<p>Please try again later. If this continues to" +
              " happen, please report it to your administrator.</p>",
              data);
}


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
    function doCall() {
        if (options.buttons) {
            options.buttons.attr("disabled", true);
        }

        if (!options.noActivityIndicator) {
            $("#activity-indicator")
                .text((options.type || options.type == "GET")
                      ? "Loading..." : "Saving...")
                .show();
        }

        var data = $.extend(true, {
            url: options.url || (SITE_ROOT + "api/json" + options.path),
            data: options.data || {dummy: ""},
            dataType: options.dataType || "json",
            error: function(xhr, textStatus, errorThrown) {
                showServerError(options.errorPrefix + " " + xhr.status + " " +
                                xhr.statusText,
                                xhr.responseText);

                if ($.isFunction(options.error)) {
                    options.error(xhr, textStatus, errorThrown);
                }
            },
            complete: function(xhr, status) {
                if (options.buttons) {
                    options.buttons.attr("disabled", false);
                }

                if (!options.noActivityIndicator) {
                    $("#activity-indicator")
                        .delay(1000)
                        .fadeOut("fast");
                }

                if ($.isFunction(options.complete)) {
                    options.complete(xhr, status);
                }

                $.funcQueue("rbapicall").next();
            }
        }, options);

        if (options.form) {
            options.form.ajaxSubmit(data);
        } else {
            $.ajax(data);
        }
    }

    options.type = options.type || "POST";

    if (options.type == "POST" || options.type == "PUT") {
        $.funcQueue("rbapicall").add(doCall);
        $.funcQueue("rbapicall").start();
    } else {
        doCall();
    }
}


/*
 * Creates a form dialog based on serialized form field data.
 * This will handle creating and managing a form dialog and posting the
 * resulting data to the server.
 *
 * options has the following fields:
 *
 *    action       - The action. Defaults to "."
 *    confirmLabel - The label on the confirm button.
 *    fields       - The serialized field data.
 *    path         - The path to post to.
 *    success      - The success function. By default, this reloads the page.
 *    title        - The form title.
 *    upload       - true if this is an upload form.
 *    width        - The optional set width of the form.
 *
 * options.fields is a dictionary with the following fields:
 *
 *    name      - The name of the field.
 *    hidden    - true if this is a hidden field.
 *    label     - The label tag for the field.
 *    required  - true if this field is required.
 *    help_text - Optional help text.
 *    widget    - The HTML for the field.
 *
 * @param {object} options  The options for the dialog.
 *
 * @return {jQuery} The form dialog.
 */
$.fn.formDlg = function(options) {
    options = $.extend({
        action: ".",
        confirmLabel: "Send",
        fields: {},
        path: "",
        success: function() { window.location.reload(); },
        title: "",
        upload: false,
        width: null
    }, options);

    return this.each(function() {
        var self = $(this);

        var errors = $("<div/>")
            .addClass("error")
            .hide();

        var form = $("<form/>")
            .attr("action", options.action)
            .submit(function(e) {
                send();
                return false;
            })
            .append($("<table/>")
                .append($("<colgroup/>")
                    .append('<col/>')
                    .append('<col/>')
                    .append('<col width="100%"/>'))
                .append($("<tbody/>")));

        if (options.upload) {
            form.attr({
                encoding: "multipart/form-data",
                enctype:  "multipart/form-data"
            });
        }

        var tbody = $("tbody", form);

        var fieldInfo = {};

        for (var i = 0; i < options.fields.length; i++) {
            var field = options.fields[i];
            fieldInfo[field.name] = {'field': field};

            if (field.hidden) {
                form.append($(field.widget));
            } else {
                fieldInfo[field.name].row =
                    $("<tr/>")
                        .appendTo(tbody)
                        .append($("<td/>")
                            .addClass("label")
                            .html(field.label))
                        .append($("<td/>")
                            .html(field.widget))
                        .append($("<td/>")
                            .append($("<ul/>")
                                .addClass("errorlist")
                                .hide()));

                if (field.required) {
                    $("label", fieldInfo[field.name].row)
                        .addClass("required");
                }

                if (field.help_text) {
                    $("<tr/>")
                        .appendTo(tbody)
                        .append("<td/>")
                        .append($("<td/>")
                            .addClass("help")
                            .attr("colspan", 2)
                            .text(field.help_text));
                }
            }
        }

        var box = $("<div/>")
            .addClass("formdlg")
            .append(errors)
            .append(self)
            .append(form)
            .keypress(function(e) {
                e.stopPropagation();
            });

        if (options.width) {
            box.width(options.width);
        }

        box.modalBox({
            title: options.title,
            buttons: [
                $('<input type="button"/>')
                    .val("Cancel"),
                $('<input type="button"/>')
                    .val(options.confirmLabel)
                    .click(function() {
                        form.submit();
                        return false;
                    })
            ]
        });

        /*
         * Sends the form data to the server.
         */
        function send() {
            rbApiCall({
                path: options.path,
                form: form,
                buttons: $("input:button", self.modalBox("buttons")),
                errorPrefix: "Saving the form failed due to a server error:",
                success: function(rsp) {
                    checkForErrors(rsp);
                }
            });
        }


        /*
         * Checks the server response for errors, displaying any on the form.
         *
         * @param {object} rsp  The server response.
         */
        function checkForErrors(rsp) {
            if (rsp.stat == "ok") {
                options.success(rsp);
                box.remove();
            } else if (rsp.fields) {
                errors
                    .html(rsp.err.msg)
                    .show();

                for (var fieldName in rsp.fields) {
                    if (!fieldInfo[fieldName]) {
                        continue;
                    }

                    var list = $(".errorlist", fieldInfo[fieldName].row)
                        .css("display", "block");

                    for (var i = 0; i < rsp.fields[fieldName].length; i++) {
                        $("<li/>")
                            .appendTo(list)
                            .html(rsp.fields[fieldName][i]);
                    }
                }
            }
        }
    });
};


/*
 * Toggles whether an object is starred. Right now, we support
 * "reviewrequests" and "groups" types.
 *
 * @param {string} type      The type used for constructing the path.
 * @param {string} objid     The object ID to star/unstar.
 * @param {bool}   default_  The default value.
 */
$.fn.toggleStar = function(type, objid, default_) {
    return this.each(function() {
        var self = $(this);

        // Constants
        var STAR_ON_IMG = MEDIA_URL + "rb/images/star_on.png?" + MEDIA_SERIAL;
        var STAR_OFF_IMG = MEDIA_URL + "rb/images/star_off.png?" + MEDIA_SERIAL;

        var on = default_;
        var baseURL = "/" + type + "/" + objid;

        self.click(function() {
            on = !on;

            rbApiCall({
                path: baseURL + (on ? "/star/" : "/unstar/"),
                data: {}
            });

            self.attr("src", (on ? STAR_ON_IMG : STAR_OFF_IMG));
        });
    });
};

$(document).ready(function() {
    $('<div id="activity-indicator" />')
        .text("Loading...")
        .hide()
        .appendTo("body");
});

// vim: set et:sw=4:
