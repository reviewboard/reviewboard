/**
 * Utilities for interfacing with the Review Board API.
 */

import {
    type DialogView,
    craft,
    paint,
} from '@beanbag/ink';

import { UserSession } from '../models/userSessionModel';


/**
 * An extended XHR object that includes API-related error fields.
 *
 * Version Added:
 *     8.0
 */
interface ExtendedXHR extends JQueryXHR {
    /** The payload from the API response. */
    errorPayload?: Record<string, unknown>;

    /** The error text from the API response. */
    errorText?: string;
}


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

    let xhr: XMLHttpRequest;

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
                for (const field in xhrFields) {
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
                for (const [key, header] of Object.entries(headers)) {
                    xhr.setRequestHeader(key, headers[key]);
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
 * Options for the setActivityIndicator method.
 *
 * Version Added:
 *     8.0
 */
export interface SetActivityIndicatorOptions {
    /**
     * The activity indicator element.
     *
     * This is used for unit testing.
     * */
    _$activityIndicator?: JQuery;

    /**
     * Whether to hide the indicator immediately instead of on a delay.
     *
     * This is used for unit testing.
     */
    _activityIndicatorHideImmediately?: boolean;

    /**
     * True if the indicator should be suppressed, even if ``enabled`` is true.
     */
    noActivityIndicator?: boolean;

    /**
     * The type of HTTP request that the indicator is representing.
     */
    type?: 'DELETE' | 'GET' | 'HEAD' | 'POST' | 'PUT';
}


/**
 * Enable or disable the activity indicator.
 *
 * Users should prefer importing API and calling
 * :js:func:`API.setActivityIndicator` instead of
 * :js:func:`RB.setActivityIndicator`.
 *
 * Args:
 *     enabled (boolean):
 *         Whether the activity indicator should be enabled.
 *
 *     options (object):
 *         Additional options.
 */
export function setActivityIndicator(
    enabled: boolean,
    options: SetActivityIndicatorOptions,
) {
    const $activityIndicator = options._$activityIndicator ||
                               $('#activity-indicator');

    if (enabled) {
        if (ajaxOptions.enableIndicator && !options.noActivityIndicator) {
            $activityIndicator.children('.indicator-text')
                .text((options.type && options.type === 'GET')
                      ? _`Loading...` : _`Saving...`);

            $activityIndicator
                .removeClass('error')
                .show();
        }
    } else if (ajaxOptions.enableIndicator &&
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
}


/**
 * Options for the API.request method.
 *
 * Version Added:
 *     8.0
 */
export interface APIRequestOptions
extends JQuery.AjaxSettings, SetActivityIndicatorOptions {
    /** Any buttons to disable while the API request is in flight. */
    buttons?: JQuery;

    /** Additional data to send with the request. */
    data?: JQuery.PlainObject;

    /** A form to submit, if any. */
    form?: JQuery;

    /** The relative path from the server name to the API endpoint. */
    path?: string;

    /** The prefix for the API path (after ``SITE_ROOT`, before ``api``). */
    prefix?: string;

    /**
     * The type of HTTP request to make.
     *
     * Defaults to ``POST``.
     */
    type?: 'DELETE' | 'GET' | 'HEAD' | 'POST' | 'PUT';
}


/**
 * Make an API request.
 *
 * This will handle any button disabling/enabling, write to the correct path
 * prefix, do form uploading, and display server errors.
 *
 * Users should prefer importing API and calling :js:func:`API.request` instead
 * of :js:func:`RB.apiCall`.
 *
 * Args:
 *     options (APIRequestOptions):
 *         Options for the API request.
 */
export function apiCall(
    options: APIRequestOptions,
) {
    const prefix = options.prefix || '';
    const url = options.url || (SITE_ROOT + prefix + 'api' + options.path);

    function showErrorPage(xhr: XMLHttpRequestEventMap, data: string) {
        const requestData = options.data ? $.param(options.data) : '(none)';
        const body1 = paint<HTMLElement>([
            _`
                There may be useful error details below. The following error
                page may be useful to your system administrator or when
                <a href="https://www.reviewboard.org/bugs/new/">reporting a
                bug</a>. To save the page, right-click the error below and
                choose "Save Page As," if available, or "View Source" and
                save the result as a <tt>.html</tt> file.
            `,
        ]);
        const body2 = paint<HTMLElement>([
            _`
                <b>Warning:</b>
                Be sure to remove any sensitive material that may exist in
                the error page before reporting a bug!
            `,
        ]);

        const dialog = craft<DialogView>`
            <Ink.Dialog title=${_`Server Error Details`}
                        id="server-error-box"
                        onClose=${() => dialog.remove()}
                        size="max">
             <Ink.Dialog.Body>
              <div>${body1}</div>
              <div>${body2}</div>
              <div>
               <b>${_`Error Code:`}</b> ${' '} ${xhr.status.toString()}
              </div>
              <div>
               <b>${_`Error Text:`}</b> ${' '} ${xhr.statusText}
              </div>
              <div>
               <b>${_`Request URL:`}</b> ${' '} ${url}
              </div>
              <div>
               <b>${_`Request Data:`}</b> ${' '} ${requestData}
              </div>
              <div>
               <b>${_`Response Data:`}</b>
              </p>
              <iframe></iframe>
             </Ink.Dialog.Body>
             <Ink.Dialog.PrimaryActions>
              <Ink.DialogAction action="close">
               ${_`Close`}
              </Ink.DialogAction>
             </Ink.Dialog.PrimaryActions>
            </Ink.Dialog>
        `;

        dialog.open();

        const iframe = dialog.el.querySelector('iframe');
        const doc = (iframe.contentDocument ||
                     iframe.contentWindow.document);
        doc.open();
        doc.write(data);
        doc.close();
    }

    function doCall() {
        const $activityIndicator = options._$activityIndicator ||
                                   $('#activity-indicator');

        if (options.buttons) {
            options.buttons.prop('disabled', true);
        }

        setActivityIndicator(true, options);

        const defaultOptions = {
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
                    .text(_`A server error occurred.`)
                    .append(
                        $('<a role="button" href="#">')
                            .text(_`Show Details`)
                            .on('click',
                                () => showErrorPage(xhr, responseText))
                    )
                    .append(
                        $('<a role="button" href="#">')
                            .text(_`Dismiss`)
                            .on('click', () => {
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
            url: url,
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

                setActivityIndicator(false, options);

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
        UserSession.instance.get('readOnly')) {
        console.error('%s request not sent. Site is in read-only mode.',
                      options.type);
        return;
    }

    // We allow disabling the function queue for the sake of unit tests.
    if (ajaxOptions.enableQueuing && options.type !== 'GET') {
        $.funcQueue('rbapicall').add(doCall);
        $.funcQueue('rbapicall').start();
    } else {
        doCall();
    }
}

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
export function storeAPIError(xhr: ExtendedXHR) {
    try {
        const rsp = JSON.parse(xhr.responseText);
        xhr.errorPayload = rsp;
        xhr.errorText = rsp.err.msg;
    } catch (e) {
        xhr.errorPayload = null;
        xhr.errorText = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
    }
}


/**
 * Global options for ajax operations.
 */
export const ajaxOptions = {
    enableIndicator: true,
    enableQueuing: true,
};


/*
 * Call API.request instead of $.ajax.
 *
 * We wrap instead of assign, and we explicitly use "API.request" instead of
 * "apiCall" in order to allow unit tests to create spies for the function.
 *
 * TODO: for typing purposes, we really ought to be overriding Backbone.sync
 * instead of Backbone.ajax. The built-in sync implementation assumes that
 * Backbone.ajax returns an XHR and uses that to trigger the 'request' event on
 * the model. We don't currently use that event at all, but we don't care about
 * the other features of the built-in sync method.
 *
 * This would also allow us to modify the backbone type definitions to define
 * sync result as generic so we could override things to use promise results
 * instead of jqXHR where appropriate.
 */
Backbone.ajax = options => API.request(options);


/**
 * An error class to wrap the error triplet that comes from Backbone calls.
 *
 * Version Added:
 *     5.0
 */
export class BackboneError extends Error {
    /**********************
     * Instance variables *
     **********************/

    /** The model or collection that the call was made on. */
    modelOrCollection: unknown;

    /** Any options that were passed to the call. */
    options: unknown;

    /** The XMLHttpRequest wrapper object. */
    xhr: ExtendedXHR;

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
    constructor(
        modelOrCollection: unknown,
        xhr: ExtendedXHR,
        options: unknown,
    ) {
        super(xhr.errorText);

        this.modelOrCollection = modelOrCollection;
        this.xhr = xhr;
        this.options = options;
    }
}


/* Store it as a global for backwards compatibility. */
window.BackboneError = BackboneError;


/**
 * Adapt promises to old-style callbacks.
 *
 * This is a utility method to wrap a callable that supports returning a
 * promise to continue to support old-style success/ready/error/complete
 * callbacks.
 *
 * Users should prefer importing API and calling
 * :js:func:`API.promiseToCallbacks` instead of
 * :js:func:`RB.promiseToCallbacks`.
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
export function promiseToCallbacks<T>(
    options: {
        complete?: () => void;
        error?: (
            modelOrCollection: unknown,
            xhr: JQueryXHR,
            options: unknown,
        ) => void;
        ready?: (result: T) => void;
        success?: (result: T) => void;
    },
    context: unknown,
    callable: (options: unknown) => Promise<T>,
) {
    callable(_.omit(options, ['success', 'ready', 'error', 'complete']))
        .then(result => {
            if (typeof options.success === 'function') {
                options.success.call(context, result);
            } else if (typeof options.ready === 'function') {
                options.ready.call(context, result);
            }
        })
        .catch((err: BackboneError) => {
            if (typeof options.error === 'function') {
                options.error.call(context, err.modelOrCollection,
                                   err.xhr, err.options);
            }
        })
        .finally(() => {
            if (typeof options.complete === 'function') {
                options.complete.call(context);
            }
        });
}


/**
 * Container object for API methods.
 *
 * This is used to facilitate unit tests so jasmine can spy on these methods.
 *
 * Version Added:
 *     8.0
 */
export const API = {
    promiseToCallbacks,
    request: apiCall,
    setActivityIndicator,
    storeError: storeAPIError,
};
