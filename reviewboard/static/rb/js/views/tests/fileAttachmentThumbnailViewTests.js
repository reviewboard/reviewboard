suite('rb/views/FileAttachmentThumbnail', function() {
    var reviewRequest,
        model,
        view;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest();
        model = new RB.FileAttachment({
            downloadURL: 'http://example.com/file.png',
            filename: 'file.png'
        });

        spyOn(model, 'trigger').andCallThrough();
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
            var $el = $('<div/>')
                .addClass(RB.FileAttachmentThumbnail.prototype.className)
                .html(RB.FileAttachmentThumbnail.prototype.template(
                    _.defaults({
                        caption: 'No caption',
                        captionClass: 'edit empty-caption'
                    }, model.attributes)));

            model.set('loaded', true);

            view = new RB.FileAttachmentThumbnail({
                renderThumbnail: true,
                reviewRequest: reviewRequest,
                el: $el,
                model: model
            });
            $testsScratch.append(view.$el);
            view.render();

            expectElements();

            expect(view.$('.file-actions').is(':visible')).toBe(true);
            expect(view.$('.fa-spinner').length).toBe(0);
        });

        it('Rendered thumbnail with unloaded model', function() {
            view = new RB.FileAttachmentThumbnail({
                reviewRequest: reviewRequest,
                renderThumbnail: true,
                model: model
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
                model.set('caption', 'My Caption');
                model.set('loaded', true);
                model.url = '/api/file-attachments/123/';
            });

            it('With review UI', function() {
                model.set('reviewURL', '/review/');

                view = new RB.FileAttachmentThumbnail({
                    reviewRequest: reviewRequest,
                    renderThumbnail: true,
                    model: model
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
                view = new RB.FileAttachmentThumbnail({
                    reviewRequest: reviewRequest,
                    renderThumbnail: true,
                    model: model
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
            model.set('loaded', true);
            model.url = '/api/file-attachments/123/';

            view = new RB.FileAttachmentThumbnail({
                canEdit: true,
                reviewRequest: reviewRequest,
                renderThumbnail: true,
                model: model
            });
            $testsScratch.append(view.$el);
            view.render();

            spyOn(view, 'trigger').andCallThrough();
        });

        it('Begin caption editing', function() {
            view._$caption.inlineEditor('startEdit');
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');
        });

        it('Cancel caption editing', function() {
            view._$caption.inlineEditor('startEdit');
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');

            view._$caption.inlineEditor('cancel');
            expect(view.trigger).toHaveBeenCalledWith('endEdit');
        });

        it('Save caption', function() {
            spyOn(model, 'save');

            view._$caption.inlineEditor('startEdit');
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');

            view.$('input')
                .val('Foo')
                .triggerHandler('keyup');
            view._$caption.inlineEditor('submit');

            expect(view.trigger).toHaveBeenCalledWith('endEdit');
            expect(model.get('caption')).toBe('Foo');
            expect(model.save).toHaveBeenCalled();
        });

        it('Delete', function() {
            spyOn(model, 'destroy').andCallThrough();
            spyOn($, 'ajax').andCallFake(function(options) {
                options.success();
            });
            spyOn(view.$el, 'fadeOut').andCallFake(function(done) {
                done();
            });

            spyOn(view, 'remove');

            view.$('.file-delete').click();

            expect($.ajax).toHaveBeenCalled();
            expect(model.destroy).toHaveBeenCalled();
            expect(model.trigger.calls[2].args[0]).toBe('destroying');
            expect(view.$el.fadeOut).toHaveBeenCalled();
            expect(view.remove).toHaveBeenCalled();
        });
    });
});
