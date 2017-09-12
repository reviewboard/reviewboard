suite('rb/pages/views/ReviewablePageView', function() {
    const pageTemplate = dedent`
        <div id="review-banner"></div>
        <a href="#" id="review-action">Edit Review</a>
        <a href="#" id="ship-it-action">Ship It</a>
    `;

    let $editReview;
    let $shipIt;
    let page;
    let pageView;

    beforeEach(function() {
        const $container = $('<div/>')
            .html(pageTemplate)
            .appendTo($testsScratch);

        RB.DnDUploader.instance = null;

        $editReview = $container.find('#review-action');
        $shipIt = $container.find('#ship-it-action');

        page = new RB.ReviewablePage({
            checkForUpdates: false,
            reviewRequestData: {
                id: 123,
                loaded: true,
                state: RB.ReviewRequest.PENDING,
            },
            editorData: {
                mutableByUser: true,
                statusMutableByUser: true,
            },
        }, {
            parse: true,
        });

        pageView = new RB.ReviewablePageView({
            el: $container,
            model: page,
        });

        const reviewRequest = page.get('reviewRequest');

        spyOn(reviewRequest, 'ready').and.callFake(
            (options, context) => options.ready.call(context));

        pageView.render();
    });

    afterEach(function() {
        RB.DnDUploader.instance = null;

        pageView.remove();
    });

    describe('Public objects', function() {
        it('reviewRequest', function() {
            expect(page.get('reviewRequest')).not.toBe(undefined);
        });

        it('pendingReview', function() {
            const pendingReview = page.get('pendingReview');

            expect(pendingReview).not.toBe(undefined);
            expect(pendingReview.get('parentObject'))
                .toBe(page.get('reviewRequest'));
        });

        it('commentIssueManager', function() {
            expect(page.commentIssueManager).not.toBe(undefined);
            expect(page.commentIssueManager.get('reviewRequest'))
                .toBe(page.get('reviewRequest'));
        });

        it('reviewRequestEditor', function() {
            const reviewRequestEditor = page.reviewRequestEditor;

            expect(reviewRequestEditor).not.toBe(undefined);
            expect(reviewRequestEditor.get('reviewRequest'))
                .toBe(page.get('reviewRequest'));
            expect(reviewRequestEditor.get('commentIssueManager'))
                .toBe(page.commentIssueManager);
            expect(reviewRequestEditor.get('editable')).toBe(true);
        });

        it('reviewRequestEditorView', function() {
            expect(pageView.reviewRequestEditorView).not.toBe(undefined);
            expect(pageView.reviewRequestEditorView.model)
                .toBe(page.reviewRequestEditor);
        });
    });

    describe('Actions', function() {
        it('Edit Review', function() {
            spyOn(RB.ReviewDialogView, 'create');

            $editReview.click();

            expect(RB.ReviewDialogView.create).toHaveBeenCalled();

            const options = RB.ReviewDialogView.create.calls.argsFor(0)[0];
            expect(options.review).toBe(page.get('pendingReview'));
            expect(options.reviewRequestEditor).toBe(page.reviewRequestEditor);
        });

        describe('Ship It', function() {
            let pendingReview;

            beforeEach(function() {
                pendingReview = page.get('pendingReview');
            });

            it('Confirmed', function() {
                spyOn(window, 'confirm').and.returnValue(true);
                spyOn(pendingReview, 'ready').and.callFake(
                    (options, context) => options.ready.call(context));
                spyOn(pendingReview, 'save').and.callFake(
                    (options, context) => options.success.call(context));
                spyOn(pendingReview, 'publish').and.callThrough();
                spyOn(pageView.draftReviewBanner, 'hideAndReload');

                $shipIt.click();

                expect(window.confirm).toHaveBeenCalled();
                expect(pendingReview.ready).toHaveBeenCalled();
                expect(pendingReview.publish).toHaveBeenCalled();
                expect(pendingReview.save).toHaveBeenCalled();
                expect(pageView.draftReviewBanner.hideAndReload)
                    .toHaveBeenCalled();
                expect(pendingReview.get('shipIt')).toBe(true);
                expect(pendingReview.get('bodyTop')).toBe('Ship It!');
            });

            it('Canceled', function() {
                spyOn(window, 'confirm').and.returnValue(false);
                spyOn(pendingReview, 'ready');

                $shipIt.click();

                expect(window.confirm).toHaveBeenCalled();
                expect(pendingReview.ready).not.toHaveBeenCalled();
            });
        });
    });

    describe('Update bubble', function() {
        const summary = 'My summary';
        const user = {
            url: '/users/foo/',
            fullname: 'Mr. User',
            username: 'user',
        };
        let $bubble;
        let bubbleView;

        beforeEach(function() {
            page.get('reviewRequest').trigger('updated', {
                summary: summary,
                user: user,
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
                const info = {
                    user: {
                        fullname: 'Hello',
                    },
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
