import { suite } from '@beanbag/jasmine-suites';
import { BaseModel, spina } from '@beanbag/spina';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { ExtraDataMixin } from 'reviewboard/common';


suite('rb/models/ExtraData', function() {
    let model;

    describe('With Backbone.Model.extend', function() {
        beforeEach(function() {
            const Resource = Backbone.Model.extend(_.defaults({
                defaults() {
                    return {
                        extraData: {},
                    };
                },

                initialize() {
                    this._setupExtraData();
                },
            }, ExtraDataMixin));

            model = new Resource();
        });

        it('change events fired', function() {
            const callbacks = {
                'change': function() {},
                'change:extraData': function() {},
            };

            spyOn(callbacks, 'change');
            spyOn(callbacks, 'change:extraData');

            model.on('change', callbacks.change);
            model.on('change:extraData', callbacks['change:extraData']);

            model.setExtraData('foo', 1);

            expect(callbacks.change).toHaveBeenCalled();
            expect(callbacks['change:extraData']).toHaveBeenCalled();
        });

        it('attributes updated', function() {
            const oldExtraData = model.attributes.extraData;

            expect(model.extraData.attributes).toBe(oldExtraData);

            model.set({
                extraData: {
                    foo: 1,
                },
            });

            expect(model.attributes.extraData).toEqual({foo: 1});
            expect(model.extraData.attributes).toEqual({foo: 1});

            expect(model.extraData.attributes).not.toBe(oldExtraData);
            expect(model.attributes.extraData).not.toBe(oldExtraData);

            expect(model.extraData.attributes)
                .toBe(model.attributes.extraData);
        });
    });

    describe('With spina BaseModel', function() {
        beforeEach(function() {
            @spina({ mixins: [ExtraDataMixin] })
            class Resource extends BaseModel {
                defaults() {
                    return {
                        extraData: {},
                    };
                }

                initialize() {
                    this._setupExtraData();
                }
            }

            model = new Resource();
        });

        it('change events fired', function() {
            const callbacks = {
                'change': function() {},
                'change:extraData': function() {},
            };

            spyOn(callbacks, 'change');
            spyOn(callbacks, 'change:extraData');

            model.on('change', callbacks.change);
            model.on('change:extraData', callbacks['change:extraData']);

            model.setExtraData('foo', 1);

            expect(callbacks.change).toHaveBeenCalled();
            expect(callbacks['change:extraData']).toHaveBeenCalled();
        });

        it('attributes updated', function() {
            const oldExtraData = model.attributes.extraData;

            expect(model.extraData.attributes).toBe(oldExtraData);

            model.set({
                extraData: {
                    foo: 1,
                },
            });

            expect(model.attributes.extraData).toEqual({foo: 1});
            expect(model.extraData.attributes).toEqual({foo: 1});

            expect(model.extraData.attributes).not.toBe(oldExtraData);
            expect(model.attributes.extraData).not.toBe(oldExtraData);

            expect(model.extraData.attributes)
                .toBe(model.attributes.extraData);
        });
    });
});
