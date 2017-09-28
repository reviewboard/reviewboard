/**
 * jQuery AJAX transport for receiving Blob and ArrayBuffer data.
 *
 * XMLHttpRequest2 supports receiving binary data represented by
 * :js:class:`Blob` and :js:class:`ArrayBuffer`. This transport enabled binary
 * data support through standard :js:func:`jQuery.ajax` calls.
 */
$.ajaxTransport('arraybuffer blob', function(options, origOptions, jqXHR) {
    if (!window.FormData) {
        return null;
    }

    let xhr;

    return {
        send(headers, completeCB) {
            xhr = options.xhr();
            xhr.addEventListener('load', () => {
                const result = {};
                result[options.dataType] = xhr.response;

                completeCB(xhr.status, xhr.statusText, result,
                           xhr.getAllResponseHeaders());
            });

            if (options.username) {
                xhr.open(options.type, options.url, options.async,
                         options.username, options.password);
            } else {
                xhr.open(options.type, options.url, options.async);
            }

            xhr.responseType = options.dataType;

            /* Apply any custom fields that may be provided. */
            const xhrFields = options.xhrFields;

            if (xhrFields) {
                for (let field in xhrFields) {
                    if (xhrFields.hasOwnProperty(field)) {
                        xhr[field] = xhrFields[field];
                    }
                }
            }

            if (!options.crossDomain && !headers['X-Requested-With']) {
                headers['X-Requested-With'] = 'XMLHttpRequest';
            }

            /*
             * Catch errors with cross-domain requests, like jQuery does.
             */
            try {
                for (let key in headers) {
                    if (headers.hasOwnProperty(key)) {
                        xhr.setRequestHeader(key, headers[key]);
                    }
                }
            } catch (e) {}

            xhr.send(options.hasContent ? options.data : null);
        },

        abort() {
            if (xhr && xhr.readyState !== 4) {
                xhr.abort();
            }
        },
    };
});


/**
 * Enable or disable the activity indicator.
 *
 * Args:
 *     enabled (boolean):
 *         Whether the activity indicator should be enabled.
 *
 *     options (object):
 *         Additional options.
 *
 * Option Args:
 *     noActivityIndicator (boolean):
 *         True if the indicator should be suppressed, even if ``enabled`` is
 *         true.
 *
 *     type (string):
 *         The type of HTTP request that the indicator is representing. This
 *         will be either ``GET`` (loading) or ``POST`` (saving).
 */
RB.setActivityIndicator = function(enabled, options) {
    const $activityIndicator = $('#activity-indicator');

    if (enabled) {
        if (RB.ajaxOptions.enableIndicator && !options.noActivityIndicator) {
            $activityIndicator.children('.indicator-text')
                .text((options.type && options.type === 'GET')
                      ? gettext('Loading...') : gettext('Saving...'));

            $activityIndicator
                .removeClass('error')
                .show();
        }
    } else if (RB.ajaxOptions.enableIndicator &&
               !options.noActivityIndicator &&
               !$activityIndicator.hasClass('error')) {
        $activityIndicator
            .delay(250)
            .fadeOut('fast');
    }
};


/**
 * Make an API request.
 *
 * This will handle any button disabling/enabling, write to the correct path
 * prefix, do form uploading, and display server errors.
 *
 * Args:
 *     options (object):
 *         Options for the API request.
 *
 * Option Args:
 *     buttons (jQuery):
 *         Any buttons to disable while the API request is in flight.
 *
 *     form (jQuery):
 *         A form to submit, if any.
 *
 *     type (string):
 *         The type of HTTP request to make. Defaults to ``POST``.
 *
 *     prefix (string):
 *         The prefix for the API path (after ``SITE_ROOT``, before ``api``).
 *
 *     path (string):
 *         The relative path from the server name to the Review Board API
 *         endpoint.
 *
 *     data (object):
 *         Additional data to send with the request.
 *
 *     success (function):
 *         An optional success callback. If not specified, the default handler
 *         will reload the page.
 *
 *     error (function):
 *         An optional error callback, to be called after the error banner is
 *         displayed.
 *
 *     complete (function):
 *         An optional complete callback, which is called after the success or
 *         error callbacks.
 */
RB.apiCall = function(options) {
    const prefix = options.prefix || '';
    const url = options.url || (SITE_ROOT + prefix + 'api' + options.path);

    function showErrorPage(xhr, data) {
        const $iframe = $('<iframe/>').width('100%');
        const requestData = options.data ? $.param(options.data) : '(none)';

        $('<div class="server-error-box"/>')
            .appendTo(document.body)
            .append('<p><b>' + gettext('Error Code:') + '</b> ' + xhr.status + '</p>')
            .append('<p><b>' + gettext('Error Text:') + '</b> ' + xhr.statusText + '</p>')
            .append('<p><b>' + gettext('Request URL:') + '</b> ' + url + '</p>')
            .append('<p><b>' + gettext('Request Data:') + '</b> ' + requestData + '</p>')
            .append('<p class="response-data"><b>' + gettext('Response Data:') + '</b></p>')
            .append(gettext('<p>There may be useful error details below. The following error page may be useful to your system administrator or when <a href="https://www.reviewboard.org/bugs/new/">reporting a bug</a>. To save the page, right-click the error below and choose "Save Page As," if available, or "View Source" and save the result as a <tt>.html</tt> file.</p>'))
            .append(gettext('<p><b>Warning:</b> Be sure to remove any sensitive material that may exist in the error page before reporting a bug!</p>'))
            .append($iframe)
            .on('resize', function() {
                $iframe.height($(this).height() - $iframe.position().top);
            })
            .modalBox({
                stretchX: true,
                stretchY: true,
                title: gettext('Server Error Details')
            });

        const doc = $iframe[0].contentDocument || $iframe[0].contentWindow.document;
        doc.open();
        doc.write(data);
        doc.close();
    }

    function doCall() {
        const $activityIndicator = $('#activity-indicator');

        if (options.buttons) {
            options.buttons.attr('disabled', true);
        }

        RB.setActivityIndicator(true, options);

        const data = $.extend(true, {
            url: url,
            data: options.data,
            dataType: options.dataType || 'json',
            error: function(xhr, textStatus, errorThrown) {
                const responseText = xhr.responseText;

                let rsp = null;
                try {
                    rsp = JSON.parse(responseText);
                } catch (e) {
                }

                if ((rsp && rsp.stat) || xhr.status === 204) {
                    if (_.isFunction(options.success)) {
                        options.success(rsp, xhr.status);
                    }

                    return;
                }

                $activityIndicator
                    .addClass('error')
                    .text(gettext('A server error occurred.'))
                    .append(
                        $('<a href="#" />')
                            .text(gettext('Show Details'))
                            .click(() => showErrorPage(xhr, responseText))
                    )
                    .append(
                        $('<a href="#" />')
                            .text(gettext('Dismiss'))
                            .click(function() {
                                $activityIndicator.fadeOut('fast');
                                return false;
                            })
                    );

                if (_.isFunction(options.error)) {
                    options.error(xhr, textStatus, errorThrown);
                }
            },
            complete: function(xhr, status) {
                if (options.buttons) {
                    options.buttons.attr('disabled', false);
                }

                RB.setActivityIndicator(false, options);

                if (_.isFunction(options.complete)) {
                    options.complete(xhr, status);
                }

                $.funcQueue('rbapicall').next();
            }
        }, options);

        if (data.data === null || data.data === undefined ||
            (data.data instanceof Object &&
             !(window.Blob && data.data instanceof Blob))) {
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

    options.type = options.type || 'POST';

    if (options.type !== 'GET' && options.type !== 'HEAD' &&
        RB.UserSession.instance.get('readOnly')) {
        console.error('%s request not sent. Site is in read-only mode.',
                      options.type);
        return;
    }

    // We allow disabling the function queue for the sake of unit tests.
    if (RB.ajaxOptions.enableQueuing && options.type !== 'GET') {
        $.funcQueue('rbapicall').add(doCall);
        $.funcQueue('rbapicall').start();
    } else {
        doCall();
    }
};

/**
 * Parse API error information from a response and stores it.
 *
 * The xhr object provided will be extended with two new attributes:
 * 'errorText' and 'errorPayload'. These represent the response's error
 * message and full error payload, respectively.
 *
 * Args:
 *     xhr (jqXHR):
 *         The XMLHttpRequest object.
 */
RB.storeAPIError = function(xhr) {
    try {
        const rsp = JSON.parse(xhr.responseText);
        xhr.errorPayload = rsp;
        xhr.errorText = rsp.err.msg;
    } catch (e) {
        xhr.errorPayload = null;
        xhr.errorText = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
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
Backbone.ajax = options => RB.apiCall(options);


// vim: set et:sw=4:
