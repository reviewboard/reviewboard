import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { FileAttachment } from 'reviewboard/common';

import { FileAttachmentThumbnailView } from '../fileAttachmentThumbnailView';


declare const $testsScratch: JQuery;


suite('rb/views/FileAttachmentThumbnailView', function() {
    let reviewRequest: RB.ReviewRequest;
    let model: FileAttachment;
    let view: FileAttachmentThumbnailView;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest();
        model = new FileAttachment({
            downloadURL: 'http://example.com/file.png',
            filename: 'file.png',
        });

        spyOn(model, 'trigger').and.callThrough();
    });

    describe('Rendering', function() {
        function expectElements() {
            expect(view.$('a.edit').length).toBe(1);
            expect(view.$('.file-caption').length).toBe(1);
            expect(view.$('.file-actions').length).toBe(1);
            expect(view.$('.file-delete').length).toBe(
                view.options.canEdit && model.get('loaded') ? 1 : 0);
            expect(view.$('.file-update').length).toBe(
                view.options.canEdit && model.get('loaded') ? 1 : 0);
        }

        function expectAttributeMatches() {
            expect(view.$('.file-download').attr('href')).toBe(
                model.get('downloadURL'));
            expect(view.$('.file-caption .edit').text()).toBe(
                model.get('caption'));
        }

        it('Using existing elements', function() {
            const $el = $('<div/>')
                .addClass(FileAttachmentThumbnailView.prototype.className)
                .html(FileAttachmentThumbnailView.prototype.template(
                    _.defaults({
                        caption: 'No caption',
                        captionClass: 'edit empty-caption',
                    }, model.attributes)));

            model.set('loaded', true);

            view = new FileAttachmentThumbnailView({
                el: $el,
                model: model,
                renderThumbnail: true,
                reviewRequest: reviewRequest,
            });
            $testsScratch.append(view.$el);
            view.render();

            expectElements();

            expect(view.$('.file-actions').is(':visible')).toBe(true);
            expect(view.$('.fa-spinner').length).toBe(0);
        });

        it('Rendered thumbnail with unloaded model', function() {
            view = new FileAttachmentThumbnailView({
                model: model,
                renderThumbnail: true,
                reviewRequest: reviewRequest,
            });
            $testsScratch.append(view.$el);
            view.render();

            expectElements();

            expect(view.$('.file-actions').children().length).toBe(0);
            expect(view.$('.fa-spinner').length).toBe(1);
        });

        describe('Rendered thumbnail with loaded model', function() {
            beforeEach(function() {
                model.id = 123;
                model.attributes.id = 123;
                model.set('caption', 'My Caption');
                model.set('loaded', true);
                model.url = '/api/file-attachments/123/';
            });

            it('With review UI', function() {
                model.set('reviewURL', '/review/');

                view = new FileAttachmentThumbnailView({
                    model: model,
                    renderThumbnail: true,
                    reviewRequest: reviewRequest,
                });
                $testsScratch.append(view.$el);
                view.render();

                expectElements();
                expectAttributeMatches();

                expect(view.$('.file-actions').children().length).toBe(2);
                expect(view.$('.fa-spinner').length).toBe(0);
                expect(view.$('.file-review').length).toBe(1);
                expect(view.$('.file-add-comment').length).toBe(0);
            });

            it('No review UI', function() {
                view = new FileAttachmentThumbnailView({
                    model: model,
                    renderThumbnail: true,
                    reviewRequest: reviewRequest,
                });
                $testsScratch.append(view.$el);
                view.render();

                expectElements();
                expectAttributeMatches();

                expect(view.$('.file-actions').children().length).toBe(2);
                expect(view.$('.fa-spinner').length).toBe(0);
                expect(view.$('.file-review').length).toBe(0);
                expect(view.$('.file-add-comment').length).toBe(1);
            });
        });
    });

    describe('Actions', function() {
        beforeEach(function() {
            model.id = 123;
            model.attributes.id = 123;
            model.set('loaded', true);
            model.url = '/api/file-attachments/123/';

            view = new FileAttachmentThumbnailView({
                canEdit: true,
                model: model,
                renderThumbnail: true,
                reviewRequest: reviewRequest,
            });
            $testsScratch.append(view.$el);
            view.render();

            spyOn(view, 'trigger').and.callThrough();
        });

        it('Begin caption editing', function() {
            view._captionEditorView.startEdit();
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');
        });

        it('Cancel caption editing', function() {
            view._captionEditorView.startEdit();
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');

            view._captionEditorView.cancel();
            expect(view.trigger).toHaveBeenCalledWith('endEdit');
        });

        it('Save caption', function(done) {
            spyOn(model, 'save').and.callFake(() => {
                expect(view.trigger).toHaveBeenCalledWith('endEdit');
                expect(model.get('caption')).toBe('Foo');
                expect(model.save).toHaveBeenCalled();

                done();
            });

            view._captionEditorView.startEdit();
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');

            view.$('input')
                .val('Foo')
                .triggerHandler('keyup');

            view._captionEditorView.submit();
        });

        it('Delete', function(done) {
            spyOn(model, 'destroy').and.callThrough();
            spyOn($, 'ajax').and.callFake(options => options.success());
            spyOn(view.$el, 'fadeOut').and.callFake(done => done());
            spyOn(view, 'remove').and.callFake(() => {
                expect($.ajax).toHaveBeenCalled();
                expect(model.destroy).toHaveBeenCalled();
                expect(model.trigger.calls.argsFor(2)[0]).toBe('destroying');
                expect(view.$el.fadeOut).toHaveBeenCalled();

                done();
            });

            view.$('.file-delete').click();
        });
    });

    describe('addAction', function() {
        beforeEach(function() {
            model.id = 123;
            model.attributes.id = 123;
            model.set('loaded', true);
            model.url = '/api/file-attachments/123/';

            view = new FileAttachmentThumbnailView({
                canEdit: true,
                model: model,
                renderThumbnail: true,
                reviewRequest: reviewRequest,
            });
            $testsScratch.append(view.$el);
            view.render();
        });

        it('After the download action', function() {
            const oldActionsLength = view._$actions.children().length;

            /*
             * The file-download class is on the inner <a> element
             * instead of the <li> element.
             */
            view.addAction(
                'file-download',
                'new-action',
                '<a href="#">New Action</a>');
            const newAction = view.$('li.new-action');

            expect(newAction.length).toBe(1);
            expect(newAction.find('a').attr('href')).toBe('#');
            expect(newAction.find('a').text()).toBe('New Action');
            expect(newAction.parent().attr('class'))
                .toEqual(view._$actions.attr('class'));
            expect(view._$actions.children().length)
                .toBe(oldActionsLength + 1);
            expect(newAction.prev().find('a').attr('class'))
                .toEqual('file-download');
        });

        it('After the delete action', function() {
            const oldActionsLength = view._$actions.children().length;

            /* The file-delete class is on the <li> element. */
            view.addAction(
                'file-delete',
                'new-action',
                '<a href="#">New Action</a>');
            const newAction = view.$('li.new-action');

            expect(newAction.length).toBe(1);
            expect(newAction.find('a').attr('href')).toBe('#');
            expect(newAction.find('a').text()).toBe('New Action');
            expect(newAction.parent().attr('class'))
                .toEqual(view._$actions.attr('class'));
            expect(view._$actions.children().length)
                .toBe(oldActionsLength + 1);
            expect(newAction.prev().attr('class')).toEqual('file-delete');
        });

        it('After one that does not exist', function() {
            const oldActionsLength = view._$actions.children().length;

            view.addAction(
                'non-existing-action',
                'new-action',
                '<a href="#">New Action</a>');
            const newAction = view.$('li.new-action');

            expect(newAction.length).toBe(0);
            expect(view._$actions.children().length)
                .toBe(oldActionsLength);
        });

        it('With one that already exists', function() {
            const oldActionsLength = view._$actions.children().length;

            view.addAction(
                'file-delete',
                'new-action',
                '<a href="#">New Action</a>');
            let newAction = view.$('li.new-action');

            expect(newAction.length).toBe(1);
            expect(newAction.find('a').attr('href')).toBe('#');
            expect(newAction.find('a').text()).toBe('New Action');
            expect(newAction.parent().attr('class'))
                .toEqual(view._$actions.attr('class'));
            expect(view._$actions.children().length)
                .toBe(oldActionsLength + 1);
            expect(newAction.prev().attr('class')).toEqual('file-delete');

            /* Add the action again, with some different content. */
            view.addAction(
                'file-delete',
                'new-action',
                '<a href="link">Changed Action</a>');
            newAction = view.$('li.new-action');

            expect(newAction.length).toBe(1);
            expect(newAction.find('a').attr('href')).toBe('link');
            expect(newAction.find('a').text()).toBe('Changed Action');
            expect(newAction.parent().attr('class'))
                .toEqual(view._$actions.attr('class'));
            expect(view._$actions.children().length)
                .toBe(oldActionsLength + 1);
            expect(newAction.prev().attr('class')).toEqual('file-delete');
        });

        it('When another thumbnail for the same file exists', function() {
            const view2 = new FileAttachmentThumbnailView({
                canEdit: false,
                model: model,
                renderThumbnail: true,
                reviewRequest: reviewRequest,
            });
            $testsScratch.append(view2.$el);
            view2.render();

            const viewOldActionsLength = view._$actions.children().length;
            const view2OldActionsLength = view2._$actions.children().length;

            view.addAction(
                'file-delete',
                'new-action',
                '<a href="#">New Action</a>');
            const newAction = view.$('li.new-action');
            const newAction2 = view2.$('li.new-action');

            /* Check the first thumbnail. */
            expect(newAction.length).toBe(1);
            expect(newAction.find('a').attr('href')).toBe('#');
            expect(newAction.find('a').text()).toBe('New Action');
            expect(newAction.parent().attr('class'))
                .toEqual(view._$actions.attr('class'));
            expect(view._$actions.children().length)
                .toBe(viewOldActionsLength + 1);
            expect(newAction.prev().attr('class')).toEqual('file-delete');

            /* Check the second thumbnail. The action should not exist here. */
            expect(newAction2.length).toBe(0);
            expect(view2._$actions.children().length)
                .toBe(view2OldActionsLength);
        });
    });
});
