/**
 * Unit tests for rb/utils/apiUtils.
 *
 * Version Added:
 *     5.0
 */
suite('rb/utils/apiUtils', function() {
    const STATUS_TEXTS = {
        200: 'OK',
        400: 'Bad Request',
        404: 'Not Found',
        500: 'Internal Server Error',
    };

    let oldEnableQueuing;
    let oldEnableIndicator;

    beforeEach(function() {
        oldEnableQueuing = RB.ajaxOptions.enableQueuing;
        oldEnableIndicator = RB.ajaxOptions.enableIndicator;

        RB.ajaxOptions.enableQueuing = true;
        RB.ajaxOptions.enableIndicator = true;
    });

    afterEach(function() {
        RB.ajaxOptions.enableQueuing = oldEnableQueuing;
        RB.ajaxOptions.enableIndicator = oldEnableIndicator;
    });


    /**
     * Set up a call to $.ajax.
     *
     * This spies on :js:func:`$.ajax`, creating a mock implementation which
     * will prepare a mock XHR object and call the right handlers for the
     * right HTTP status codes.
     *
     * Args:
     *     options (object):
     *         Options for the AJAX call.
     *
     * Option Args:
     *     method (string, optional):
     *         The HTTP method expected. This defaults to "POST".
     *
     *     responseText (string, optional):
     *         An optional string for the response, if not setting ``rsp``.
     *
     *     rsp (object, optional):
     *         An optional JSON payload for the response.
     *
     *     statusCode (number, optional):
     *         The optional HTTP status code for the response. This default to
     *         200.
     */
    function setupAjaxCall(options) {
        spyOn($, 'ajax').and.callFake(request => {
            expect(request.type).toBe(options.method || 'POST');

            const rsp = options.rsp;
            const statusCode = options.statusCode || 200;
            const xhr = {
                _isXHR: true,
                status: statusCode,
                statusText: STATUS_TEXTS[statusCode],
            };

            if (rsp !== undefined) {
                xhr.responseText = JSON.stringify(rsp);
            } else {
                xhr.responseText = options.responseText || '';
            }

            /*
             * This roughly matches what $.ajax sets. It's good enough for our
             * purposes.
             */
            let statusText;

            if (statusCode === 204 || request.type === 'HEAD') {
                statusText = 'nocontent';
            } else if (statusCode === 304) {
                statusText = 'notmodified';
            } else if (statusCode >= 200 && statusCode < 300) {
                statusText = 'success';
            } else {
                statusText = 'error';
            }

            /* Invoke the handlers. */
            if ((statusCode >= 200 && statusCode < 300) || statusCode === 304) {
                /* Currently, there isn't always a default success handler. */
                if (request.success !== undefined) {
                    request.success(
                        (rsp !== undefined ? rsp : options.responseText),
                        statusText,
                        xhr);
                }
            } else {
                /* Currently, there's always a default error handler. */
                request.error(xhr, statusText, xhr.statusText);
            }

            request.complete(xhr, statusText);
        });
    }

    describe('apiCall', function() {
        /**
         * Run a RB.apiCall test.
         *
         * This sets up a call to :js:func:`RB.apiCall` with a mock AJAX
         * implementation and UI. It handles checking all the common state
         * in the UI and the callbacks, matching expectations against provided
         * arguments.
         *
         * Args:
         *     done (function):
         *         The done handler for the test.
         *
         *     options (object):
         *         Options for the test.
         *
         * Option Args:
         *     addErrorHandler (boolean, optional):
         *         Whether to register an error handler. The default is
         *         ``true``.
         *
         *     addSuccessHandler (boolean, optional):
         *         Whether to register a success handler. The default is
         *         ``true``.
         *
         *     expectedStatusText (string):
         *         The expected status text for callbacks.
         *
         *     expectActivityIndicatorError (boolean, optional):
         *         Whether to expect that the activity indicator will display
         *         an error. The default is ``false``.
         *
         *     expectAPIErrorSuccess (boolean, optional):
         *         Whether to expect the success handler to be called with API
         *         error information. The default is ``false``.
         *
         *     expectSuccess (boolean, optional):
         *         Whether to expect the success handler to be called. The
         *         default is ``false``.
         *
         *     method (string, optional):
         *         The HTTP method expected. This defaults to "POST".
         *
         *     responseText (string, optional):
         *         An optional string for the response, if not setting ``rsp``.
         *
         *     rsp (object, optional):
         *         An optional JSON payload for the response.
         *
         *     statusCode (number, optional):
         *         The optional HTTP status code for the response. This
         *         defaults to 200.
         */
        function runAPICallTest(done, options) {
            const $buttons = $('<button>');
            const $activityIndicator =
                $('<div><span class="indicator-text"></span></div>')
                    .css('display', 'none')
                    .appendTo($testsScratch);

            /*
             * Define this early so that we trigger a warning with the
             * usage in runCommonSuccessErrorChecks().
             */
            let data;

            setupAjaxCall(options);

            function runCommonSuccessErrorChecks() {
                /* Check the order of calls. */
                expect(data.complete).not.toHaveBeenCalled();

                expect($buttons.attr('disabled')).toBe('disabled');
                expect($activityIndicator.hasClass('error')).toBe(false);
                expect($activityIndicator.find('.indicator-text').text()).toBe(
                    (options.method === 'GET'
                     ? 'Loading...'
                     : 'Saving...'));
            }

            data = {
                path: 'info/',
                type: options.method,
                buttons: $buttons,
                _$activityIndicator: $activityIndicator,
                _activityIndicatorHideImmediately: true,
                complete: function(xhr, statusText) {
                    expect(xhr._isXHR).toBeTrue();
                    expect(statusText).toBe(options.expectedStatusText);

                    /* Check the order of calls. */
                    if (options.expectSuccess) {
                        if (data.success !== undefined) {
                            expect(data.success).toHaveBeenCalled();
                        }
                    } else {
                        if (data.error !== undefined) {
                            expect(data.error).toHaveBeenCalled();
                        }
                    }

                    /* Check DOM state from RB.apiCall. */
                    expect($buttons.attr('disabled')).toBeUndefined();

                    const activityIndicatorHasError =
                        $activityIndicator.hasClass('error');
                    const activityIndicatorDisplay =
                        $activityIndicator.css('display');

                    if (options.expectActivityIndicatorError) {
                        expect(activityIndicatorHasError).toBeTrue();
                        expect(activityIndicatorDisplay).toBe('block');
                    } else {
                        expect(activityIndicatorHasError).toBeFalse();
                        expect(activityIndicatorDisplay).toBe('none');
                    }

                    /*
                     * Make sure that queue functionality doesn't break by
                     * incorporating it into the test's done handler.
                     */
                    if (options.method === 'GET') {
                        /* GETs aren't in a queue. */
                        done();
                    } else {
                        $.funcQueue('rbapicall').add(function() {
                            $.funcQueue('rbapicall').clear();

                            done();
                        });
                    }
                }
            };

            if (options.addSuccessHandler !== false) {
                data.success = function(rsp, statusText, xhr) {
                    if (options.expectSuccess) {
                        runCommonSuccessErrorChecks();

                        if (options.expectAPIErrorSuccess) {
                            expect(arguments.length).toBe(2);
                            expect(arguments[1]).toBe(options.statusCode);
                        } else {
                            expect(arguments.length).toBe(3);
                            expect(arguments[1])
                                .toBe(options.expectedStatusText);
                            expect(arguments[2]._isXHR).toBeTrue();
                        }

                        expect(arguments[0]).toEqual(options.rsp);
                    } else {
                        done.fail('API call unexpectedly returned success.');
                    }
                };
            }

            if (options.addErrorHandler !== false) {
                data.error = function(xhr, statusText, httpStatusText) {
                    if (options.expectSuccess) {
                        done.fail('API call unexpectedly returned error.');
                    } else {
                        runCommonSuccessErrorChecks();

                        expect(statusText).toBe(options.expectedStatusText);
                        expect(xhr._isXHR).toBeTrue();

                        /*
                         * This seems like a tautology, given the setup code,
                         * but we're making sure it's preserved through
                         * RB.apiCall's handlers.
                         */
                        expect(httpStatusText).toBe(STATUS_TEXTS[xhr.status]);
                        expect(xhr.statusText).toBe(httpStatusText);
                    }
                };
            }

            spyOn(data, 'complete').and.callThrough();

            if (data.success !== undefined) {
                spyOn(data, 'success').and.callThrough();
            }

            if (data.error !== undefined) {
                spyOn(data, 'error').and.callThrough();
            }

            RB.apiCall(data);
        }

        /**
         * Add a suite of RB.apiCall tests for a given HTTP method.
         *
         * Args:
         *     method (string):
         *         The HTTP method being tested.
         *
         *     successText (string):
         *         The status text expected on success.
         *
         *     errorText (string):
         *         The status text expected on error.
         */
        function addAPICallTests(method, successText, errorText) {
            describe(`HTTP ${method}`, function() {
                describe('With success', function() {
                    it('And success handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                rsp: {
                                    stat: 'ok',
                                },
                                expectSuccess: true,
                                expectedStatusText: successText,
                            });
                    });

                    it('And no success handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                rsp: {
                                    stat: 'ok',
                                },
                                addSuccessHandler: false,
                                expectSuccess: true,
                                expectedStatusText: successText,
                            });
                    });
                });

                describe('With HTTP 204', function() {
                    it('And success handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                statusCode: 204,
                                expectSuccess: true,
                                expectedStatusText: 'nocontent',
                            });
                    });

                    it('And no success handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                statusCode: 204,
                                addSuccessHandler: false,
                                expectSuccess: true,
                                expectedStatusText: 'nocontent',
                            });
                    });
                });

                describe('With API error', function() {
                    it('And error handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                rsp: {
                                    stat: 'fail',
                                },
                                statusCode: 404,
                                expectSuccess: false,
                                expectedStatusText: errorText,
                            });
                    });

                    it('And no error handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                rsp: {
                                    stat: 'fail',
                                },
                                statusCode: 404,
                                addErrorHandler: false,
                                expectSuccess: true,
                                expectAPIErrorSuccess: true,
                                expectedStatusText: errorText,
                            });
                    });
                });

                describe('With unexpected error', function() {
                    it('With error handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                responseText: 'oh no it broke',
                                statusCode: 500,
                                expectSuccess: false,
                                expectedStatusText: errorText,
                            });
                    });

                    it('Without error handler', function(done) {
                        runAPICallTest(
                            done,
                            {
                                method: method,
                                responseText: 'oh no it broke',
                                statusCode: 500,
                                addErrorHandler: false,
                                expectSuccess: false,
                                expectedStatusText: errorText,
                                expectActivityIndicatorError: true,
                            });
                    });
                });
            });
        }

        ['DELETE', 'GET', 'POST', 'PATCH', 'PUT'].forEach(
            method => addAPICallTests(method, 'success', 'error'));

        addAPICallTests('HEAD', 'nocontent', 'nocontent');
    });
});
