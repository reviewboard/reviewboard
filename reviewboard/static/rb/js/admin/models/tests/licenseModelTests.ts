import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    expectAsync,
    it,
    spyOn,
} from 'jasmine-core';

import {
    CallLicenseActionError,
    License,
    LicenseCheckStatus,
    LicenseCollection,
} from 'reviewboard/admin';


suite('rb/admin/models/License', () => {
    let model: License;
    let collection: LicenseCollection;

    beforeEach(() => {
        collection = new LicenseCollection();

        model = new License({
            actionTarget: 'provider1:license1',
            licenseID: 'license1',
            productName: 'Test Product',
            summary: 'License summary',
        }, {
            actionCSRFToken: 'abc123',
        });
        collection.add(model);
    });

    describe('Methods', () => {
        describe('callAction', () => {
            it('With success', async () => {
                spyOn(window, 'fetch').and.callFake(async (url, options) => {
                    expect(options.method).toBe('POST');
                    expect(Array.from(options.body.entries())).toEqual([
                        ['action', 'my-action'],
                        ['action_target', 'provider1:license1'],
                        ['csrfmiddlewaretoken', 'abc123'],
                        ['action_data', '{"arg1":"value1","arg2":"value2"}'],
                    ]);

                    return new Response(
                        '{"fields": 123}',
                        {
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        }
                    );
                });

                const rsp = await model.callAction({
                    action: 'my-action',
                    args: {
                        arg1: 'value1',
                        arg2: 'value2',
                    },
                });

                expect(rsp).toEqual({
                    fields: 123,
                });

                expect(fetch).toHaveBeenCalled();
            });

            it('With error message', async () => {
                spyOn(window, 'fetch').and.callFake(async (url, options) => {
                    expect(options.method).toBe('POST');
                    expect(Array.from(options.body.entries())).toEqual([
                        ['action', 'my-action'],
                        ['action_target', 'provider1:license1'],
                        ['csrfmiddlewaretoken', 'abc123'],
                    ]);

                    return new Response(
                        '{"error": "Bad things happened!"}',
                        {
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            status: 400,
                        }
                    );
                });

                await expectAsync(model.callAction({
                    action: 'my-action',
                })).toBeRejectedWithError(
                    CallLicenseActionError,
                    'Bad things happened!',
                );
            });

            it('With invalid response payload', async () => {
                spyOn(window, 'fetch').and.callFake(async (url, options) => {
                    expect(options.method).toBe('POST');
                    expect(Array.from(options.body.entries())).toEqual([
                        ['action', 'my-action'],
                        ['action_target', 'provider1:license1'],
                        ['csrfmiddlewaretoken', 'abc123'],
                    ]);

                    return new Response(
                        'XXX',
                        {
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        }
                    );
                });

                await expectAsync(model.callAction({
                    action: 'my-action',
                })).toBeRejectedWithError(
                    CallLicenseActionError,
                    'Error performing license action "my-action"',
                );
            });

            it('With HTTP error response', async () => {
                spyOn(window, 'fetch').and.callFake(async (url, options) => {
                    expect(options.method).toBe('POST');
                    expect(Array.from(options.body.entries())).toEqual([
                        ['action', 'my-action'],
                        ['action_target', 'provider1:license1'],
                        ['csrfmiddlewaretoken', 'abc123'],
                    ]);

                    return new Response(
                        '{}',
                        {
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            status: 400,
                        }
                    );
                });

                await expectAsync(model.callAction({
                    action: 'my-action',
                })).toBeRejectedWithError(
                    CallLicenseActionError,
                    'Error performing license action "my-action"',
                );
            });
        });

        describe('checkForUpdates', () => {
            let seenStatuses: string[];

            beforeEach(() => {
                seenStatuses = [];

                model.on('change:checkStatus',
                         (model, value) => seenStatuses.push(value));

                spyOn(model, 'trigger').and.callThrough();

                spyOn(window, 'fetch').and.callFake(async (url, options) => {
                    expect(url).toBe('https://example.com/check/');
                    expect(options.method).toBe('POST');
                    expect(Array.from(options.body.entries())).toEqual([
                        ['key1', 'value1'],
                        ['key2', 'value2'],
                    ]);
                    expect(Object.hasOwn(options, 'credentials')).toBeFalse();
                    expect(Object.hasOwn(options, 'headers')).toBeFalse();

                    return new Response(
                        '{"resultKey1": "value1", "resultKey2": "value2"}',
                        {
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        }
                    );
                });
            });

            it('With canCheck=false', async () => {
                spyOn(model, 'callAction').and.returnValues(
                    Promise.resolve({
                        canCheck: false,
                    }),
                );

                await model.checkForUpdates();

                expect(model.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);

                expect(seenStatuses).toEqual([
                    LicenseCheckStatus.CHECKING,
                    LicenseCheckStatus.HAS_LATEST,
                ]);

                expect(model.trigger)
                    .not.toHaveBeenCalledWith('licenseUpdated');

                expect(model.callAction).toHaveBeenCalledOnceWith({
                    action: 'license-update-check',
                });
                expect(fetch).not.toHaveBeenCalled();
            });

            it('With optional fetch control', async () => {
                spyOn(model, 'callAction').and.returnValues(
                    Promise.resolve({
                        canCheck: true,
                        checkStatusURL: 'https://example.com/check/',
                        credentials: {
                            password: 'ZZ9PZA',
                            username: 'ford',
                        },
                        data: {
                            key1: 'value1',
                            key2: 'value2',
                        },
                        headers: {
                            'X-Gimme-License': 'please',
                        },
                    }),
                    Promise.resolve({
                        status: 'has-latest',
                    }),
                );

                fetch.and.callFake(async (url, options) => {
                    expect(url).toBe('https://example.com/check/');
                    expect(options.method).toBe('POST');
                    expect(options.headers).toEqual({
                        'X-Gimme-License': 'please',
                    });
                    expect(options.credentials).toEqual({
                        password: 'ZZ9PZA',
                        username: 'ford',
                    });
                    expect(Array.from(options.body.entries())).toEqual([
                        ['key1', 'value1'],
                        ['key2', 'value2'],
                    ]);

                    return new Response(
                        JSON.stringify({
                            resultKey1: 'value1',
                            resultKey2: 'value2',
                        }),
                        {
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        }
                    );
                });

                await model.checkForUpdates();

                expect(model.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);

                expect(seenStatuses).toEqual([
                    LicenseCheckStatus.CHECKING,
                    LicenseCheckStatus.APPLYING,
                    LicenseCheckStatus.HAS_LATEST,
                ]);

                expect(model.trigger)
                    .not.toHaveBeenCalledWith('licenseUpdated');

                expect(model.callAction.calls.argsFor(0)).toEqual([
                    {
                        action: 'license-update-check',
                    },
                ]);
                expect(fetch).toHaveBeenCalledTimes(1);
                expect(model.callAction.calls.argsFor(1)).toEqual([
                    {
                        action: 'process-license-update',
                        args: {
                            check_request_data: {
                                key1: 'value1',
                                key2: 'value2',
                            },
                            check_response_data: {
                                resultKey1: 'value1',
                                resultKey2: 'value2',
                            },
                            session_token: null,
                        },
                    },
                ]);
            });

            it('With no updates', async () => {
                spyOn(model, 'callAction').and.returnValues(
                    Promise.resolve({
                        canCheck: true,
                        checkStatusURL: 'https://example.com/check/',
                        data: {
                            key1: 'value1',
                            key2: 'value2',
                        },
                    }),
                    Promise.resolve({
                        status: 'has-latest',
                    }),
                );

                await model.checkForUpdates();

                expect(model.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);

                expect(seenStatuses).toEqual([
                    LicenseCheckStatus.CHECKING,
                    LicenseCheckStatus.APPLYING,
                    LicenseCheckStatus.HAS_LATEST,
                ]);

                expect(model.trigger)
                    .not.toHaveBeenCalledWith('licenseUpdated');

                expect(model.callAction.calls.argsFor(0)).toEqual([
                    {
                        action: 'license-update-check',
                    },
                ]);
                expect(fetch).toHaveBeenCalledTimes(1);
                expect(model.callAction.calls.argsFor(1)).toEqual([
                    {
                        action: 'process-license-update',
                        args: {
                            check_request_data: {
                                key1: 'value1',
                                key2: 'value2',
                            },
                            check_response_data: {
                                resultKey1: 'value1',
                                resultKey2: 'value2',
                            },
                            session_token: null,
                        },
                    },
                ]);
            });

            it('With update applied', async () => {
                spyOn(model, 'callAction').and.returnValues(
                    Promise.resolve({
                        canCheck: true,
                        checkStatusURL: 'https://example.com/check/',
                        data: {
                            key1: 'value1',
                            key2: 'value2',
                        },
                    }),
                    Promise.resolve({
                        license_infos: {
                            license1: {
                                licenseID: 'license1',
                                summary: 'New summary',
                            },
                        },
                        status: 'applied',
                    }),
                );

                await model.checkForUpdates();

                expect(model.get('checkStatus'))
                    .toBe(LicenseCheckStatus.APPLIED);
                expect(model.get('summary')).toBe('New summary');

                expect(seenStatuses).toEqual([
                    LicenseCheckStatus.CHECKING,
                    LicenseCheckStatus.APPLYING,
                    LicenseCheckStatus.APPLIED,
                ]);

                expect(model.trigger).toHaveBeenCalledWith('licenseUpdated');

                expect(model.callAction.calls.argsFor(0)).toEqual([
                    {
                        action: 'license-update-check',
                    },
                ]);
                expect(fetch).toHaveBeenCalledTimes(1);
                expect(model.callAction.calls.argsFor(1)).toEqual([
                    {
                        action: 'process-license-update',
                        args: {
                            check_request_data: {
                                key1: 'value1',
                                key2: 'value2',
                            },
                            check_response_data: {
                                resultKey1: 'value1',
                                resultKey2: 'value2',
                            },
                            session_token: null,
                        },
                    },
                ]);
            });

            it('With HTTP 403 error from license server', async () => {
                fetch.and.callFake(async (url, options) => {
                    expect(url).toBe('https://example.com/check/');
                    expect(options.method).toBe('POST');
                    expect(Array.from(options.body.entries())).toEqual([
                        ['key1', 'value1'],
                        ['key2', 'value2'],
                    ]);

                    return new Response(
                        '{}',
                        {
                            status: 403,
                        }
                    );
                });

                spyOn(model, 'callAction').and.returnValues(
                    Promise.resolve({
                        canCheck: true,
                        checkStatusURL: 'https://example.com/check/',
                        data: {
                            key1: 'value1',
                            key2: 'value2',
                        },
                    }),
                );

                await model.checkForUpdates();

                expect(model.get('checkStatus'))
                    .toBe(LicenseCheckStatus.NO_LICENSE);

                expect(seenStatuses).toEqual([
                    LicenseCheckStatus.CHECKING,
                    LicenseCheckStatus.NO_LICENSE,
                ]);

                expect(model.trigger)
                    .not.toHaveBeenCalledWith('licenseUpdated');

                expect(model.callAction).toHaveBeenCalledOnceWith({
                    action: 'license-update-check',
                });
                expect(fetch).toHaveBeenCalledTimes(1);
            });
        });
    });
});
