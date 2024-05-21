import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { ValidateDiffModel } from 'reviewboard/common';


suite('rb/resources/models/ValidateDiffModel', function() {
    let model: ValidateDiffModel;

    beforeEach(function() {
        model = new ValidateDiffModel();
    });

    describe('methods', function() {
        describe('url', function() {
            it('Without local site', function() {
                expect(_.result(model, 'url')).toBe('/api/validation/diffs/');
            });

            it('With local site', function() {
                model.set('localSitePrefix', 's/test-site/');
                expect(model.getURL())
                    .toBe('/s/test-site/api/validation/diffs/');
            });

            it('With a null local site', function() {
                model.set('localSitePrefix', null);
                expect(_.result(model, 'url')).toBe('/api/validation/diffs/');
            });
        });
    });

    describe('toJSON', function() {
        it('repository field', function() {
            model.set('repository', 123);
            const data = model.toJSON();
            expect(data.repository).toBe(123);
        });
    });
});
