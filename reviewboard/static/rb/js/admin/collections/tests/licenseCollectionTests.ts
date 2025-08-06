import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    License,
    LicenseCheckStatus,
    LicenseCollection,
} from 'reviewboard/admin';


suite('rb/admin/collections/LicenseCollection', () => {
    let license1: License;
    let license2: License;
    let license3: License;
    let collection: LicenseCollection;

    beforeEach(() => {
        collection = new LicenseCollection();

        license1 = new License({
            actionTarget: 'provider1:license1',
            checkStatus: LicenseCheckStatus.HAS_LATEST,
            licenseID: 'license1',
            productName: 'Test Product 1',
            summary: 'License summary',
        }, {
            actionCSRFToken: 'abc123',
        });
        collection.add(license1);

        license2 = new License({
            actionTarget: 'provider1:license2',
            checkStatus: LicenseCheckStatus.HAS_LATEST,
            licenseID: 'license2',
            productName: 'Test Product 2',
            summary: 'License summary',
        }, {
            actionCSRFToken: 'abc123',
        });
        collection.add(license2);

        license3 = new License({
            actionTarget: 'provider1:license3',
            checkStatus: LicenseCheckStatus.HAS_LATEST,
            licenseID: 'license3',
            productName: 'Test Product 3',
            summary: 'License summary',
        }, {
            actionCSRFToken: 'abc123',
        });
        collection.add(license3);
    });

    describe('Methods', () => {
        describe('checkForUpdates', () => {
            it('With success', async () => {
                spyOn(console, 'error');
                spyOn(license1, 'checkForUpdates').and.resolveTo();
                spyOn(license2, 'checkForUpdates').and.resolveTo();
                spyOn(license3, 'checkForUpdates').and.resolveTo();

                await collection.checkForUpdates();

                expect(license1.checkForUpdates).toHaveBeenCalled();
                expect(license2.checkForUpdates).toHaveBeenCalled();
                expect(license3.checkForUpdates).toHaveBeenCalled();
                expect(console.error).not.toHaveBeenCalled();
            });

            it('With errors', async () => {
                spyOn(console, 'error');
                spyOn(license1, 'checkForUpdates').and.resolveTo();
                spyOn(license2, 'checkForUpdates').and.rejectWith(
                    new Error('oh no'));
                spyOn(license3, 'checkForUpdates').and.resolveTo();

                await collection.checkForUpdates();

                expect(license1.checkForUpdates).toHaveBeenCalled();
                expect(license2.checkForUpdates).toHaveBeenCalled();
                expect(license3.checkForUpdates).toHaveBeenCalled();
                expect(console.error).toHaveBeenCalledWith(
                    'Update check for license "%s" failed: %s',
                    'license2',
                    new Error('oh no'),
                );
            });
        });

        describe('updateLicenses', () => {
            it('With new licenses', () => {
                collection.updateLicenses({
                    license4: {
                        actionTarget: 'provider1:license4',
                        licenseID: 'license4',
                        productName: 'Test Product 4',
                        summary: 'License summary',
                    },
                });

                expect(collection.length).toBe(4);

                const license4 = collection.get('license4');
                expect(license4.get('actionTarget'))
                    .toBe('provider1:license4');
                expect(license4.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);
                expect(license4.get('licenseID')).toBe('license4');
                expect(license4.get('productName')).toBe('Test Product 4');
                expect(license4.get('summary')).toBe('License summary');
            });

            it('With existing licenses', () => {
                collection.updateLicenses({
                    license2: {
                        actionTarget: 'provider1:license2',
                        licenseID: 'license2',
                        productName: 'New Test Product 2',
                        summary: 'New license summary',
                    },
                });

                expect(collection.length).toBe(3);

                const license2 = collection.get('license2');
                expect(license2.get('actionTarget'))
                    .toBe('provider1:license2');
                expect(license2.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);
                expect(license2.get('licenseID')).toBe('license2');
                expect(license2.get('productName')).toBe('New Test Product 2');
                expect(license2.get('summary')).toBe('New license summary');
            });

            it('With removed licenses', () => {
                collection.updateLicenses({
                    license2: null,
                });

                expect(collection.length).toBe(2);

                expect(collection.get('license2')).toBeUndefined();
            });

            it('With mix', () => {
                collection.updateLicenses({
                    license2: {
                        actionTarget: 'provider1:license2',
                        licenseID: 'license2',
                        productName: 'New Test Product 2',
                        summary: 'New license summary',
                    },
                    license3: null,
                    license4: {
                        actionTarget: 'provider1:license4',
                        licenseID: 'license4',
                        productName: 'Test Product 4',
                        summary: 'License summary',
                    },
                });

                expect(collection.length).toBe(3);

                const license2 = collection.get('license2');
                expect(license2.get('actionTarget'))
                    .toBe('provider1:license2');
                expect(license2.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);
                expect(license2.get('licenseID')).toBe('license2');
                expect(license2.get('productName')).toBe('New Test Product 2');
                expect(license2.get('summary')).toBe('New license summary');

                expect(collection.get('license3')).toBeUndefined();

                const license4 = collection.get('license4');
                expect(license4.get('actionTarget'))
                    .toBe('provider1:license4');
                expect(license4.get('checkStatus'))
                    .toBe(LicenseCheckStatus.HAS_LATEST);
                expect(license4.get('licenseID')).toBe('license4');
                expect(license4.get('productName')).toBe('Test Product 4');
                expect(license4.get('summary')).toBe('License summary');
            });

            it('With checkStatus', () => {
                collection.updateLicenses(
                    {
                        license2: {
                            actionTarget: 'provider1:license2',
                            licenseID: 'license2',
                            productName: 'New Test Product 2',
                            summary: 'New license summary',
                        },
                        license3: null,
                        license4: {
                            actionTarget: 'provider1:license4',
                            licenseID: 'license4',
                            productName: 'Test Product 4',
                            summary: 'License summary',
                        },
                    },
                    {
                        checkStatus: LicenseCheckStatus.APPLIED,
                    });

                expect(collection.length).toBe(3);

                const license2 = collection.get('license2');
                expect(license2.get('actionTarget'))
                    .toBe('provider1:license2');
                expect(license2.get('checkStatus'))
                    .toBe(LicenseCheckStatus.APPLIED);
                expect(license2.get('licenseID')).toBe('license2');
                expect(license2.get('productName')).toBe('New Test Product 2');
                expect(license2.get('summary')).toBe('New license summary');

                expect(collection.get('license3')).toBeUndefined();

                const license4 = collection.get('license4');
                expect(license4.get('actionTarget'))
                    .toBe('provider1:license4');
                expect(license4.get('checkStatus'))
                    .toBe(LicenseCheckStatus.APPLIED);
                expect(license4.get('licenseID')).toBe('license4');
                expect(license4.get('productName')).toBe('Test Product 4');
                expect(license4.get('summary')).toBe('License summary');
            });
        });
    });
});
