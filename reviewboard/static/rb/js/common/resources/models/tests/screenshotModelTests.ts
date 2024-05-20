import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import {
    BaseResource,
    Screenshot,
} from 'reviewboard/common';


suite('rb/resources/models/Screenshot', function() {
    let model: Screenshot;

    beforeEach(function(){
        model = new Screenshot({
            parentObject: new BaseResource({
                'public': true,
            }),
        });
    });

    describe('getDisplayName', function() {
        it('With caption', function() {
            model.set('caption', 'My Caption');

            expect(model.getDisplayName()).toBe('My Caption');
        });

        it('With filename', function() {
            model.set('filename', 'myfile.png');

            expect(model.getDisplayName()).toBe('myfile.png');
        });

        it('With caption and filename', function() {
            model.set({
                caption: 'My Caption',
                filename: 'myfile.png',
            });

            expect(model.getDisplayName()).toBe('My Caption');
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                screenshot: {
                    caption: 'my-caption',
                    filename: 'my-filename',
                    id: 42,
                    review_url: '/review-ui/',
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.caption).toBe('my-caption');
            expect(data.filename).toBe('my-filename');
            expect(data.reviewURL).toBe('/review-ui/');
        });
    });

    describe('toJSON', function() {
        describe('caption field', function() {
            it('With value', function() {
                model.set('caption', 'foo');
                const data = model.toJSON();
                expect(data.caption).toBe('foo');
            });
        });
    });
});
