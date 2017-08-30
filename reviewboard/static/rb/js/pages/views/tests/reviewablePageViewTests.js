suite('rb/pages/views/ReviewablePageView', function() {
    var pageTemplate = _.template([
            '<div id="review-banner"></div>',
            '<a href="#" id="review-action">Edit Review</a>',
            '<a href="#" id="ship-it-action">Ship It</a>',
        ].join('')),
        $editReview,
        $shipIt,
        pageView;

    beforeEach(function() {
        var $container = $('<div/>')
            .html(pageTemplate())
            .appendTo($testsScratch);

        RB.DnDUploader.instance = null;

        $editReview = $container.find('#review-action');
        $shipIt = $container.find('#ship-it-action');

        pageView = new RB.ReviewablePageView({
            el: $container,
            reviewRequestData: {
                id: 123,
                loaded: true,
                state: RB.ReviewRequest.PENDING
            },
            editorData: {
                mutableByUser: true,
                statusMutableByUser: true
            }
        });

        spyOn(pageView.reviewRequest, 'ready').and.callFake(
            function(options, context) {
                options.ready.call(context);
            });
        spyOn(pageView.reviewRequest, 'beginCheckForUpdates');

        pageView.render();
    });

    afterEach(function() {
        RB.DnDUploader.instance = null;

        pageView.remove();
    });

    describe('Public objects', function() {
        it('reviewRequest', function() {
            expect(pageView.reviewRequest).not.toBe(undefined);
        });

        it('pendingReview', function() {
            expect(pageView.pendingReview).not.toBe(undefined);
            expect(pageView.pendingReview.get('parentObject'))
                .toBe(pageView.reviewRequest);
        });

        it('commentIssueManager', function() {
            expect(pageView.commentIssueManager).not.toBe(undefined);
            expect(pageView.commentIssueManager.get('reviewRequest'))
                .toBe(pageView.reviewRequest);
        });

        it('reviewRequestEditor', function() {
            expect(pageView.reviewRequestEditor).not.toBe(undefined);
            expect(pageView.reviewRequestEditor.get('reviewRequest'))
                .toBe(pageView.reviewRequest);
            expect(pageView.reviewRequestEditor.get('commentIssueManager'))
                .toBe(pageView.commentIssueManager);
            expect(pageView.reviewRequestEditor.get('editable')).toBe(true);
        });

        it('reviewRequestEditorView', function() {
            expect(pageView.reviewRequestEditorView).not.toBe(undefined);
            expect(pageView.reviewRequestEditorView.model)
                .toBe(pageView.reviewRequestEditor);
        });
    });

    describe('Actions', function() {
        it('Edit Review', function() {
            var options;

            spyOn(RB.ReviewDialogView, 'create');

            $editReview.click();

            expect(RB.ReviewDialogView.create).toHaveBeenCalled();

            options = RB.ReviewDialogView.create.calls.argsFor(0)[0];
            expect(options.review).toBe(pageView.pendingReview);
            expect(options.reviewRequestEditor).toBe(pageView.reviewRequestEditor);
        });

        describe('Ship It', function() {
            it('Confirmed', function() {
                spyOn(window, 'confirm').and.returnValue(true);
                spyOn(pageView.pendingReview, 'ready').and.callFake(
                    function(options, context) {
                        options.ready.call(context);
                    });
                spyOn(pageView.pendingReview, 'save').and.callFake(
                    function(options, context) {
                        options.success.call(context);
                    });
                spyOn(pageView.pendingReview, 'publish').and.callThrough();
                spyOn(pageView.draftReviewBanner, 'hideAndReload');

                $shipIt.click();

                expect(window.confirm).toHaveBeenCalled();
                expect(pageView.pendingReview.ready).toHaveBeenCalled();
                expect(pageView.pendingReview.publish).toHaveBeenCalled();
                expect(pageView.pendingReview.save).toHaveBeenCalled();
                expect(pageView.draftReviewBanner.hideAndReload)
                    .toHaveBeenCalled();
                expect(pageView.pendingReview.get('shipIt')).toBe(true);
                expect(pageView.pendingReview.get('bodyTop')).toBe('Ship It!');
            });

            it('Canceled', function() {
                spyOn(window, 'confirm').and.returnValue(false);
                spyOn(pageView.pendingReview, 'ready');

                $shipIt.click();

                expect(window.confirm).toHaveBeenCalled();
                expect(pageView.pendingReview.ready).not.toHaveBeenCalled();
            });
        });
    });

    describe('Update bubble', function() {
        var summary = 'My summary',
            user = {
                url: '/users/foo/',
                fullname: 'Mr. User',
                username: 'user'
            },
            $bubble,
            bubbleView;

        beforeEach(function() {
            pageView.reviewRequest.trigger('updated', {
                summary: summary,
                user: user
            });

            $bubble = $('#updates-bubble');
            bubbleView = pageView._updatesBubble;
        });

        it('Displays', function() {
            expect($bubble.length).toBe(1);
            expect(bubbleView.$el[0]).toBe($bubble[0]);
            expect($bubble.is(':visible')).toBe(true);
            expect($bubble.find('#updates-bubble-summary').text())
                .toBe(summary);
            expect($bubble.find('#updates-bubble-user').text())
                .toBe(user.fullname);
            expect($bubble.find('#updates-bubble-user').attr('href'))
                .toBe(user.url);
        });

        describe('Actions', function() {
            it('Ignore', function() {
                spyOn(bubbleView, 'close').and.callThrough();
                spyOn(bubbleView, 'trigger').and.callThrough();
                spyOn(bubbleView, 'remove').and.callThrough();

                $bubble.find('.ignore').click();

                expect(bubbleView.close).toHaveBeenCalled();
                expect(bubbleView.remove).toHaveBeenCalled();
                expect(bubbleView.trigger).toHaveBeenCalledWith('closed');
            });

            it('Update Page displays Updates Bubble', function() {
                spyOn(bubbleView, 'trigger');

                $bubble.find('.update-page').click();

                expect(bubbleView.trigger).toHaveBeenCalledWith('updatePage');
            });

            it('Update Page calls notify if shouldNotify', function() {
                var info = {
                    user: {
                        fullname: 'Hello'
                    }
                };

                RB.NotificationManager.instance._canNotify = true;
                spyOn(RB.NotificationManager.instance, 'notify');
                spyOn(RB.NotificationManager.instance,
                      '_haveNotificationPermissions').and.returnValue(true);
                spyOn(pageView, '_showUpdatesBubble');

                pageView._onReviewRequestUpdated(info);

                expect(RB.NotificationManager.instance.notify)
                    .toHaveBeenCalled();
                expect(pageView._showUpdatesBubble).toHaveBeenCalled();
            });
        });
    });
});
