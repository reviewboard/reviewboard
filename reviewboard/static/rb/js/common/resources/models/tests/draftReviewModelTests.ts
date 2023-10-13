import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    BaseResource,
    DraftReview,
} from 'reviewboard/common';


suite('rb/resources/models/DraftReview', function() {
    let model;
    let parentObject;

    beforeEach(function() {
        parentObject = new BaseResource({
            links: {
                reviews: {
                    href: '/api/foos/',
                },
            },
        });

        model = new DraftReview({
            parentObject: parentObject,
        });
        model.rspNamespace = 'foo';
    });

    describe('Methods', function() {
        describe('ready', function() {
            beforeEach(function() {
                spyOn(Backbone.Model.prototype, 'fetch')
                    .and.callFake(options => {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
                spyOn(parentObject, 'ready').and.resolveTo();
                spyOn(model, '_retrieveDraft').and.resolveTo();
            });

            it('With isNew=true', async function() {
                expect(model.isNew()).toBe(true);
                expect(model.get('loaded')).toBe(false);

                await model.ready();

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).toHaveBeenCalled();
            });

            it('With isNew=false', async function() {
                model.set({
                    id: 123,
                });

                await model.ready();

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).not.toHaveBeenCalled();
            });

            it('With callbacks', function(done) {
                expect(model.isNew()).toBe(true);
                expect(model.get('loaded')).toBe(false);

                spyOn(console, 'warn');

                model.ready({
                    error: () => done.fail(),
                    success: () => {
                        expect(parentObject.ready).toHaveBeenCalled();
                        expect(model._retrieveDraft).toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                });
            });
        });

        describe('publish', function() {
            beforeEach(function() {
                spyOn(model, 'save').and.resolveTo();
                spyOn(model, 'ready').and.resolveTo();
            });

            it('Triggers "publishing" event before publish', async function() {
                spyOn(model, 'trigger');

                await model.publish();
                expect(model.trigger).toHaveBeenCalledWith('publishing');
            });

            it('Triggers "published" event after publish', async function() {
                spyOn(model, 'trigger');

                await model.publish();
                expect(model.trigger).toHaveBeenCalledWith('published');
            });

            it('Sets "public" to true', async function() {
                expect(model.get('public')).toBe(false);

                await model.publish();
                expect(model.get('public')).toBe(true);
            });
        });
    });
});
