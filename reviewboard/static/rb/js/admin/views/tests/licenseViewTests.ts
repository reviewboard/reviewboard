import { paint } from '@beanbag/ink';
import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    License,
    LicenseCheckStatus,
    LicenseStatus,
    LicenseView,
} from 'reviewboard/admin';


suite('rb/admin/views/LicenseView', () => {
    beforeEach(() => {
        spyOn($.fn, 'timesince').and.callFake(function() { return this; });
    });

    describe('Rendering', () => {
        afterEach(() => {
            expect($.fn.timesince).toHaveBeenCalled();
        });

        it('Unlicensed', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    licenseID: 'license1',
                    productName: 'Test Product',
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="unlicensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"></div>
                  <ul class="rb-c-license__details"></ul>
                 </div>
                </div>
            `);
        });

        it('Licensed', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    expiresDate: new Date('2025-04-23T00:00:00'),
                    gracePeriodDaysRemaining: 4,
                    licenseID: 'license1',
                    productName: 'Test Product',
                    status: LicenseStatus.LICENSED,
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="licensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"/>
                  <ul class="rb-c-license__details">
                   <li class="rb-c-license__detail">
                    <span class="rb-c-license__detail-icon ink-i-info"/>
                    <div class="rb-c-license__detail-content">
                     ${'Expires '}
                     <time class="timesince"
                           dateTime="2025-04-23T00:00:00-07:00"/>
                     ${' on Apr. 23, 2025, 12:00 AM'}
                    </div>
                   </li>
                  </ul>
                 </div>
                </div>
            `);
        });

        it('Expired (grace period)', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    expiresDate: new Date('2025-04-23T00:00:00'),
                    gracePeriodDaysRemaining: 4,
                    licenseID: 'license1',
                    productName: 'Test Product',
                    status: LicenseStatus.EXPIRED_GRACE_PERIOD,
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="expired-grace-period"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"/>
                  <ul class="rb-c-license__details">
                   <li class="rb-c-license__detail">
                    <span class="rb-c-license__detail-icon ink-i-warning"/>
                    <div class="rb-c-license__detail-content">
                     ${'Expired '}
                     <time class="timesince"
                           dateTime="2025-04-23T00:00:00-07:00"/>
                     ${' on Apr. 23, 2025, 12:00 AM. There are 4 days ' +
                       'left on your grace period.'}
                    </div>
                   </li>
                  </ul>
                 </div>
                </div>
            `);
        });

        it('Hard-expired', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    expiresDate: new Date('2025-01-01T00:00:00'),
                    licenseID: 'license1',
                    productName: 'Test Product',
                    status: LicenseStatus.HARD_EXPIRED,
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="hard-expired"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"/>
                  <ul class="rb-c-license__details">
                   <li class="rb-c-license__detail">
                    <span class="rb-c-license__detail-icon ink-i-warning"/>
                    <div class="rb-c-license__detail-content">
                     ${'Expired '}
                     <time class="timesince"
                           dateTime="2025-01-01T00:00:00-08:00"/>
                     ${' on Jan. 1, 2025, 12:00 AM'}
                    </div>
                   </li>
                  </ul>
                 </div>
                </div>
            `);
        });

        it('Notice', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    licenseID: 'license1',
                    noticeHTML: 'Watch out!',
                    productName: 'Test Product',
                    status: LicenseStatus.LICENSED,
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="licensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__notice">
                   Watch out!
                  </div>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"/>
                  <ul class="rb-c-license__details"/>
                 </div>
                </div>
            `);
        });

        it('Warning', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    licenseID: 'license1',
                    productName: 'Test Product',
                    status: LicenseStatus.LICENSED,
                    summary: 'License summary',
                    warningHTML: 'Oh no, bad things!',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license -has-warning"
                     data-status="licensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__warning">
                   Oh no, bad things!
                  </div>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"/>
                  <ul class="rb-c-license__details"/>
                 </div>
                </div>
            `);
        });

        it('Actions', () => {
            const view = new LicenseView({
                model: new License({
                    actionTarget: 'provider1:license1',
                    actions: [
                        {
                            actionID: 'action1',
                            label: 'Action 1',
                        },
                        {
                            actionID: 'action2',
                            label: 'Action 2',
                            url: 'https://example.com/action2',
                        },
                    ],
                    canUploadLicense: true,
                    licenseID: 'license1',
                    manageURL: 'https://example.com/manage/',
                    productName: 'Test Product',
                    status: LicenseStatus.LICENSED,
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                }),
            });

            view.render();
            const cid = view.cid;

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="licensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions">
                   <a class="ink-c-button -is-primary"
                      role="button"
                      href="https://example.com/manage/">
                    Manage your license
                   </a>
                   <input id="license-upload-form-field-${cid}"
                          name="license_data"
                          type="file"
                          style="display: none;"/>
                   <label htmlFor="license-upload-form-field-${cid}">
                    <button class="ink-c-button"
                            type="button">
                     Upload a new license file
                    </button>
                   </label>
                   <button class="ink-c-button" type="button">
                    Action 1
                   </button>
                   <a class="ink-c-button"
                      role="button"
                      href="https://example.com/action2">
                    Action 2
                   </a>
                  </div>
                  <ul class="rb-c-license__details"/>
                 </div>
                </div>
            `);
        });
    });

    describe('Model Events', () => {
        describe('change:checkStatus', () => {
            let model: License;
            let view: LicenseView;

            beforeEach(() => {
                model = new License({
                    actionTarget: 'provider1:license1',
                    licenseID: 'license1',
                    productName: 'Test Product',
                    summary: 'License summary',
                }, {
                    actionCSRFToken: 'abc123',
                });
                view = new LicenseView({
                    model: model,
                });

                view.render();
            });

            function testCheckStatus(
                status: LicenseCheckStatus,
                attrValue: string,
                expectedText: string,
            ) {
                it(status, () => {
                    model.set('checkStatus', status);

                    expect(view.el).toEqual(paint`
                        <div class="rb-c-license"
                             data-status="unlicensed"
                             data-check-status="${attrValue}">
                         <div class="rb-c-license__header">
                          <h3 class="rb-c-license__summary">
                           License summary
                          </h3>
                          <div class="rb-c-license__state">
                           ${expectedText}
                          </div>
                          <div class="rb-c-license__actions"></div>
                          <ul class="rb-c-license__details"></ul>
                         </div>
                        </div>
                    `);
                });
            }

            testCheckStatus(LicenseCheckStatus.NO_LICENSE,
                            'no-license',
                            'The product is not licensed.');
            testCheckStatus(LicenseCheckStatus.CHECKING,
                            'checking',
                            'Checking for updates...');
            testCheckStatus(LicenseCheckStatus.HAS_LATEST,
                            'has-latest',
                            'Your license is up-to-date.');
            testCheckStatus(LicenseCheckStatus.APPLYING,
                            'applying',
                            'Applying license update...');
            testCheckStatus(LicenseCheckStatus.APPLIED,
                            'applied',
                            'Your license has been automatically updated.');
            testCheckStatus(LicenseCheckStatus.ERROR_CHECKING,
                            'error-checking',
                            'An error occurred when trying to check for ' +
                            'license updates. Please contact support.');
            testCheckStatus(LicenseCheckStatus.ERROR_APPLYING,
                            'error-applying',
                            'An error occurred when trying to apply a ' +
                            'new license. Please contact support.');
        });

        it('licenseUpdated', () => {
            const model = new License({
                actionTarget: 'provider1:license1',
                licenseID: 'license1',
                productName: 'Test Product',
                summary: 'License summary',
            }, {
                actionCSRFToken: 'abc123',
            });
            const view = new LicenseView({
                model: model,
            });

            view.render();

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="unlicensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   License summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions"></div>
                  <ul class="rb-c-license__details"></ul>
                 </div>
                </div>
            `);

            model.set({
                actions: [
                    {
                        actionID: 'action1',
                        label: 'Action 1',
                    },
                    {
                        actionID: 'action2',
                        label: 'Action 2',
                        url: 'https://example.com/action2',
                    },
                ],
                expiresDate: new Date('2025-04-23T00:00:00'),
                gracePeriodDaysRemaining: 4,
                status: LicenseStatus.LICENSED,
                summary: 'New license summary',
            });
            model.trigger('licenseUpdated');

            expect(view.el).toEqual(paint`
                <div class="rb-c-license"
                     data-status="licensed"
                     data-check-status="has-latest">
                 <div class="rb-c-license__header">
                  <h3 class="rb-c-license__summary">
                   New license summary
                  </h3>
                  <div class="rb-c-license__state">
                   Your license is up-to-date.
                  </div>
                  <div class="rb-c-license__actions">
                   <button class="ink-c-button" type="button">
                    Action 1
                   </button>
                   <a class="ink-c-button"
                      role="button"
                      href="https://example.com/action2">
                    Action 2
                   </a>
                  </div>
                  <ul class="rb-c-license__details">
                   <li class="rb-c-license__detail">
                    <span class="rb-c-license__detail-icon ink-i-info"/>
                    <div class="rb-c-license__detail-content">
                     ${'Expires '}
                     <time class="timesince"
                           dateTime="2025-04-23T00:00:00-07:00"/>
                     ${' on Apr. 23, 2025, 12:00 AM'}
                    </div>
                   </li>
                  </ul>
                 </div>
                </div>
            `);
        });
    });
});
