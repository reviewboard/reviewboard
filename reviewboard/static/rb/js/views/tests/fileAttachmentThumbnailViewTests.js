suite('rb/views/FileAttachmentThumbnail', function() {
    var reviewRequest,
        model,
        view;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest();
        model = new RB.FileAttachment({
            downloadURL: 'http://example.com/file.png',
            iconURL: 'http://example.com/file-icon.png',
            filename: 'file.png'
        });

        spyOn(model, 'trigger').andCallThrough();
    });

    describe('Rendering', function() {
        function expectElements() {
            expect(view.$('.delete').length).toBe(
                model.get('loaded') ? 1 : 0);
            expect(view.$('a.edit').length).toBe(1);
            expect(view.$('.file-caption').length).toBe(1);
            expect(view.$('.file-header').length).toBe(1);
            expect(view.$('.actions').length).toBe(1);
        }

        function expectAttributeMatches() {
            expect(view.$('.download').attr('href')).toBe(
                model.get('downloadURL'));
            expect(view.$('.icon').attr('src')).toBe(
                model.get('iconURL'));
            expect(view.$('.filename').text()).toBe(
                model.get('filename'));
            expect(view.$('.file-caption .edit').text()).toBe(
                model.get('caption'));
        }

        function expectVisibility(visible) {
            expect(view.$('.file-header').children().is(':visible'))
                .toBe(visible);
            expect(view.$('.actions').is(':visible')).toBe(visible);
            expect(view.$('.file-caption').css('visibility'))
                .toBe(visible ? 'visible' : 'hidden');
        }

        it('Using existing elements', function() {
            var $el = $('<div/>')
                .addClass(RB.FileAttachmentThumbnail.prototype.className)
                .html(RB.FileAttachmentThumbnail.prototype.template(
                    _.defaults({
                        deleteFileText: 'Delete File',
                        noCaptionText: 'No caption'
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

            expect(view.$('.file-header').children().is(':visible'))
                .toBe(true);
            expect(view.$('.actions').is(':visible')).toBe(true);
            expect(view.$('.spinner').length).toBe(0);
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
            expectVisibility(false);

            expect(view.$('.actions').children().length).toBe(0);
            expect(view.$('.spinner').length).toBe(1);
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
                expectVisibility(true);

                expect(view.$('.actions').children().length).toBe(2);
                expect(view.$('.spinner').length).toBe(0);
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
                expectVisibility(true);

                expect(view.$('.actions').children().length).toBe(2);
                expect(view.$('.spinner').length).toBe(0);
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

            view.$('.delete').click();

            expect($.ajax).toHaveBeenCalled();
            expect(model.destroy).toHaveBeenCalled();
            expect(model.trigger.calls[2].args[0]).toBe('destroying');
            expect(view.$el.fadeOut).toHaveBeenCalled();
            expect(view.remove).toHaveBeenCalled();
        });
    });
});
