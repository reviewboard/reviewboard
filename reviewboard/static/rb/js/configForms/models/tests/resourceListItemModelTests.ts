import { suite } from '@beanbag/jasmine-suites';
import { spina } from '@beanbag/spina';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { DefaultReviewer } from 'reviewboard/common';
import {
    type DefaultReviewerAttrs,
} from 'reviewboard/common/resources/models/defaultReviewerModel';
import { ConfigFormsResourceListItem } from 'reviewboard/configForms';


suite('rb/configForms/models/ResourceListItem', function() {
    @spina
    class TestListItem extends ConfigFormsResourceListItem<
        DefaultReviewerAttrs,
        DefaultReviewer
    > {
        static syncAttrs = ['name', 'fileRegex'];
        createResource(
            attrs: DefaultReviewerAttrs,
        ): DefaultReviewer {
            return new DefaultReviewer(attrs);
        }
    }

    let resource: DefaultReviewer;

    beforeEach(function() {
        resource = new DefaultReviewer({
            fileRegex: '.*',
            name: 'my-name',
        });
    });

    describe('Synchronizing attributes', function() {
        it('On resource attribute change', function() {
            const listItem = new TestListItem({
                resource: resource,
            });

            resource.set('name', 'foo');

            expect(listItem.get('name')).toBe('foo');
        });

        describe('On creation', function() {
            it('With existing resource', function() {
                const listItem = new TestListItem({
                    fileRegex: '/foo/.*',
                    name: 'dummy',
                    resource: resource,
                });

                expect(listItem.get('name')).toBe('my-name');
                expect(listItem.get('fileRegex')).toBe('.*');
            });

            it('With created resource', function() {
                const listItem = new TestListItem({
                    fileRegex: '/foo/.*',
                    id: 123,
                    name: 'new-name',
                });

                expect(listItem.get('name')).toBe('new-name');
                expect(listItem.get('fileRegex')).toBe('/foo/.*');

                resource = listItem.get('resource');
                expect(resource.id).toBe(123);
                expect(resource.get('name')).toBe('new-name');
                expect(resource.get('fileRegex')).toBe('/foo/.*');
            });
        });
    });

    describe('Event mirroring', function() {
        let listItem: TestListItem;

        beforeEach(function() {
            listItem = new TestListItem({
                resource: resource,
            });

            spyOn(listItem, 'trigger');
        });

        it('destroy', function() {
            resource.trigger('destroy');
            expect(listItem.trigger).toHaveBeenCalledWith(
                'destroy', listItem, undefined, {});
        });

        it('request', function() {
            resource.trigger('request');
            expect(listItem.trigger).toHaveBeenCalledWith('request');
        });

        it('sync', function() {
            resource.trigger('sync');
            expect(listItem.trigger).toHaveBeenCalledWith('sync');
        });
    });
});
