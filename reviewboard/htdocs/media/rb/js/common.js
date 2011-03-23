/*
 * Creates a form dialog based on serialized form field data.
 * This will handle creating and managing a form dialog and posting the
 * resulting data to the server.
 *
 * options has the following fields:
 *
 *    action          - The action. Defaults to "."
 *    confirmLabel    - The label on the confirm button.
 *    fields          - The serialized field data.
 *    dataStoreObject - The object to edit or create.
 *    success         - The success function. By default, this reloads the page.
 *    title           - The form title.
 *    upload          - true if this is an upload form.
 *    width           - The optional set width of the form.
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
        dataStoreObject: null,
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
            options.dataStoreObject.setForm(form);
            options.dataStoreObject.save({
                buttons: $("input:button", box.modalBox("buttons")),
                success: function(rsp) {
                    options.success(rsp);
                    box.remove();
                },
                error: function(rsp) { // error
                    displayErrors(rsp);
                }
            });
        }


        /*
         * Displays errors on the form.
         *
         * @param {object} rsp  The server response.
         */
        function displayErrors(rsp) {
            var errorStr = rsp.err.msg;

            if (options.dataStoreObject.getErrorString) {
                errorStr = options.dataStoreObject.getErrorString(rsp);
            }

            errors
                .html(errorStr)
                .show();

            if (rsp.fields) {
                /* Invalid form data */
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
 * "reviewrequests" and "groups" types. Loads parameters from
 * data attributes on the element. Attaches via 'live' so it applies
 * to future stars matching the current jQuery selector.
 *
 * @param {string} object-type  The type used for constructing the path.
 * @param {string} object-id    The object ID to star/unstar.
 * @param {bool}   starred      The default value.
 */
$.fn.toggleStar = function() {
    // Constants
    var STAR_ON_IMG = MEDIA_URL + "rb/images/star_on.png?" + MEDIA_SERIAL;
    var STAR_OFF_IMG = MEDIA_URL + "rb/images/star_off.png?" + MEDIA_SERIAL;

    return this.live('click', function() {
        var self = $(this);

        var obj = self.data("rb.obj");

        if (!obj) {
            var type = self.attr("data-object-type");
            var objid = self.attr("data-object-id");

            if (type == "reviewrequests") {
                obj = new RB.ReviewRequest(objid);
            } else if (type == "groups") {
                obj = new RB.ReviewGroup(objid);
            } else {
                self.remove();
                return;
            }
        }

        var on = (parseInt(self.attr("data-starred")) == 1) ? 0 : 1;
        obj.setStarred(on);
        self.data("rb.obj", obj);

        var alt_title = on ? "Starred" : "Click to star";
        self.attr({
            src: (on ? STAR_ON_IMG : STAR_OFF_IMG),
            'data-starred': on,
            alt: alt_title,
            title: alt_title
        });
    });
};

$(document).ready(function() {
    $('<div id="activity-indicator" />')
        .text("Loading...")
        .hide()
        .appendTo("body");

    $('#submitter, .reviewer a').hover(
        function() {
            var infobox = $(this).find(".user-infobox");

            if (infobox.length > 0) {
                infobox.show();
            } else {
                infobox = $(this).append(
                   $("<div class='user-infobox loading'/>")
                       .load($(this).attr('href') + "infobox/",
                             function(responseText, textStatus) {
                                 infobox.removeClass("loading");
                             }));
            }
        },
        function() {
            $(this).find(".user-infobox").hide();
        }
    );

    $('.star').toggleStar();
});

// vim: set et:sw=4:
