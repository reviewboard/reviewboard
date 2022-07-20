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
    const $activityIndicator = options._$activityIndicator ||
                               $('#activity-indicator');

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
        if (options._activityIndicatorHideImmediately) {
            $activityIndicator.hide();
        } else {
            $activityIndicator
                .delay(250)
                .fadeOut('fast');
        }
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
        const $activityIndicator = options._$activityIndicator ||
                                   $('#activity-indicator');

        if (options.buttons) {
            options.buttons.attr('disabled', true);
        }

        RB.setActivityIndicator(true, options);

        const defaultOptions = {
            url: url,
            data: options.data,
            dataType: options.dataType || 'json',
            error: function(xhr, textStatus, errorThrown) {
                /*
                 * This is a fallback error handler, which the caller
                 * may override (Backbone.sync always will, for example).
                 *
                 * This is responsible for trying to determine if what we
                 * got was one of:
                 *
                 * 1. HTTP 204 (No Content -- in response to creating new
                 *    objects)
                 *
                 *    If so, this is considered a successful result.
                 *
                 * 2. An API error object (in which case it may not be an
                 *    "error" per se -- jQuery assumes anything not a 2xx
                 *    or 304 is an error, but other things are perfectly
                 *    valid responses to requests in our API).
                 *
                 *    If it has an API error code, we pass it up to the
                 *    success() handler for further evaluation.
                 *
                 *    This is primarily here for legacy reasons, prior to the
                 *    usage of Backbone (which should *never* end up
                 *    triggering this particular handler, if ordering of
                 *    callback registration is correct).
                 *
                 * 3. An unexpected error (proper HTTP 500, for instance).
                 *
                 *    This will display an error banner at the top of the
                 *    page.
                 *
                 * In the future, we should consolidate the error handlers
                 * in order to benefit from central management of errors and
                 * the "A server error has occurred" banner. That is going to
                 * require some careful thought, and likely opting into a
                 * mode that uses the correct behavior.
                 */
                const responseText = xhr.responseText;

                let rsp = null;
                try {
                    rsp = JSON.parse(responseText);
                } catch (e) {
                }

                if ((rsp && rsp.stat) || xhr.status === 204) {
                    /*
                     * This either looks like an API error, or it's an HTTP
                     * 204, which won't have a body.
                     *
                     * XXX Historically, we've treated anything with an API
                     *     error payload as "success", to avoid triggering
                     *     some older error handling behavior.
                     *
                     *     We'll continue to do so, but this is something we
                     *     need to rethink at a later date.
                     */
                    if (_.isFunction(options.success)) {
                        /*
                         * Note that this is not the same signature as a
                         * standard success call. That would be:
                         *
                         *     success(rsp, textStatus, xhr);
                         *
                         * This is a legacy wart, and is covered under unit
                         * tests.
                         */
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

                /*
                 * We actually probably shouldn't ever get here. This is
                 * legacy code. It's being kept Just In Case (TM), but if
                 * we're in this function right now, then options.error wasn't
                 * set.
                 *
                 * This is a candidate for dead code elimination.
                 */
                if (_.isFunction(options.error)) {
                    options.error(xhr, textStatus, errorThrown);
                }
            },
        };

        const forcedOptions = {
            complete: function(xhr, status) {
                /*
                 * This complete handler will always be called before the
                 * caller's handler. This ensures we're able to re-enable
                 * any buttons, turn off the loading activity, call the
                 * caller's handler, and then begin the next operation in
                 * the queue.
                 */
                if (options.buttons) {
                    options.buttons.attr('disabled', false);
                }

                RB.setActivityIndicator(false, options);

                if (_.isFunction(options.complete)) {
                    options.complete(xhr, status);
                }

                $.funcQueue('rbapicall').next();
            }
        };

        /*
         * Please note: Due to complex interactions with jQuery and Backbone,
         * the order in which we build this is very important. Some of this is
         * documented above, but to recap:
         *
         * 1. Options and a default error handler that should be used unless
         *    the caller wants to override behavior.
         *
         * 2. All caller-provided options that may affect this request. This
         *    will often include "error" and "success" handlers.
         *
         * 3. Options we want to ensure take precedence. This includes our
         *    "complete" handler, which must *always* run before the caller's.
         */
        const data = $.extend(true, defaultOptions, options, forcedOptions);

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


/**
 * An error class to wrap the error triplet that comes from Backbone calls.
 *
 * Version Added:
 *     5.0
 */
class BackboneError extends Error {
    /**
     * Initialize the error.
     *
     * Args:
     *     modelOrCollection (Backbone.Model or Backbone.Collection):
     *         The model or collection that the call was made on.
     *
     *     xhr (jQuery.XHR):
     *         The XMLHttpRequest wrapper object.
     *
     *     options (object):
     *         Any options that were passed to the call.
     */
    constructor(modelOrCollection, xhr, options) {
        super(xhr.errorText);

        this.modelOrCollection = modelOrCollection;
        this.xhr = xhr;
        this.options = options;
    }
}


/**
 * Adapt promises to old-style callbacks.
 *
 * This is a utility method to wrap a callable that supports returning a
 * promise to continue to support old-style success/ready/error/complete
 * callbacks.
 *
 * Version Added:
 *     5.0
 *
 * Args:
 *     options (object):
 *         Options for the operation, including callbacks.
 *
 *     context (object):
 *         Context to be used when calling callback functions.
 *
 *     callable (function):
 *         The function to call.
 */
RB.promiseToCallbacks = function(options, context, callable) {
    const success = (
        _.isFunction(options.success) ? options.success
            : _.isFunction(options.ready) ? options.ready
                : undefined);
    const error = (
        _.isFunction(options.error) ? options.error : undefined);
    const complete = (
        _.isFunction(options.complete) ? options.complete : undefined);

    callable(_.omit(options, ['success', 'ready', 'error', 'complete']))
        .then(result => {
            if (success) {
                success.call(context, result);
            }
        })
        .catch(err => {
            if (error) {
                error.call(context, err.modelOrCollection,
                           err.xhr, err.options);
            }
        })
        .finally(() => {
            if (complete) {
                complete.call(context);
            }
        });
};


// vim: set et:sw=4:
