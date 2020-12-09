suite('rb/reviewRequestPage/views/ReviewView', function() {
    const template = _.template(dedent`
        <div class="review review-request-page-entry">
         <div class="review-request-page-entry-contents">
          <div class="collapse-button"></div>
          <div class="banners">
           <input type="button" value="Publish" />
           <input type="button" value="Discard" />
          </div>
          <div class="body">
           <ol class="review-comments">
            <li>
             <div class="review-comment-details">
              <div class="review-comment">
               <pre class="reviewtext body_top"></pre>
              </div>
             </div>
             <div class="review-comment-thread">
              <div class="comment-section"
                   data-context-type="body_top"
                   data-reply-anchor-prefix="header-reply">
               <a class="add_comment_link"></a>
               <ul class="reply-comments">
                <li class="draft" data-comment-id="456">
                 <pre class="reviewtext"></pre>
                </li>
               </ul>
              </div>
             </div>
            </li>
            <li>
             <div class="review-comment-thread">
              <div class="comment-section" data-context-id="123"
                   data-context-type="diff_comments"
                   data-reply-anchor-prefix="comment">
               <a class="add_comment_link"></a>
               <ul class="reply-comments"></ul>
              </div>
             </div>
            </li>
            <li>
             <div class="review-comment-details">
              <div class="review-comment">
               <pre class="reviewtext body_bottom"></pre>
              </div>
             </div>
             <div class="review-comment-thread">
              <div class="comment-section"
                   data-context-type="body_bottom"
                   data-reply-anchor-prefix="footer-reply">
               <a class="add_comment_link"></a>
               <ul class="reply-comments"></ul>
              </div>
             </div>
            </div>
           </li>
          </ol>
         </div>
        </div>
    `);
    let view;
    let review;
    let reviewReply;

    beforeEach(function() {
        const reviewRequest = new RB.ReviewRequest();
        const editor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest,
        });

        review = reviewRequest.createReview({
            loaded: true,
            links: {
                replies: {
                    href: '/api/review/123/replies/',
                },
            },
        });

        const $el = $(template()).appendTo($testsScratch);

        reviewReply = review.createReply();

        view = new RB.ReviewRequestPage.ReviewView({
            el: $el,
            model: review,
            entryModel: new RB.ReviewRequestPage.ReviewEntry({
                review: review,
                reviewRequest: reviewRequest,
                reviewRequestEditor: editor,
            }),
        });

        view._setupNewReply(reviewReply);

        spyOn(view, 'trigger').and.callThrough();

        view.render();
    });

    describe('Model events', function() {
        it('bodyTop changed', function() {
            review.set({
                bodyTop: 'new **body** top',
                htmlTextFields: {
                    bodyTop: '<p>new <strong>body</strong> top</p>',
                },
            });

            expect(view._$bodyTop.html())
                .toBe('<p>new <strong>body</strong> top</p>');
        });

        it('bodyBottom changed', function() {
            review.set({
                bodyBottom: 'new **body** bottom',
                htmlTextFields: {
                    bodyBottom: '<p>new <strong>body</strong> bottom</p>',
                },
            });

            expect(view._$bodyBottom.html())
                .toBe('<p>new <strong>body</strong> bottom</p>');
        });

        describe('bodyTopRichText changed', function() {
            it('To true', function() {
                expect(view._$bodyTop.hasClass('rich-text')).toBe(false);
                review.set('bodyTopRichText', true);
                expect(view._$bodyTop.hasClass('rich-text')).toBe(true);
            });

            it('To false', function() {
                review.attributes.bodyTopRichText = true;
                view._$bodyTop.addClass('rich-text');

                review.set('bodyTopRichText', false);
                expect(view._$bodyTop.hasClass('rich-text')).toBe(false);
            });
        });

        describe('bodyBottomRichText changed', function() {
            it('To true', function() {
                expect(view._$bodyBottom.hasClass('rich-text')).toBe(false);
                review.set('bodyBottomRichText', true);
                expect(view._$bodyBottom.hasClass('rich-text')).toBe(true);
            });

            it('To false', function() {
                review.attributes.bodyBottomRichText = true;
                view._$bodyBottom.addClass('rich-text');

                review.set('bodyBottomRichText', false);
                expect(view._$bodyBottom.hasClass('rich-text')).toBe(false);
            });
        });
    });

    describe('Reply editors', function() {
        it('Views created', function() {
            expect(view._replyEditorViews.length).toBe(3);
        });

        it('Initial state populated', function() {
            let model = view._replyEditorViews[0].model;

            expect(model.get('anchorPrefix')).toBe('header-reply');
            expect(model.get('contextID')).toBe(null);
            expect(model.get('contextType')).toBe('body_top');
            expect(model.get('hasDraft')).toBe(true);

            model = view._replyEditorViews[1].model;
            expect(model.get('anchorPrefix')).toBe('comment');
            expect(model.get('contextID')).toBe(123);
            expect(model.get('contextType')).toBe('diff_comments');
            expect(model.get('hasDraft')).toBe(false);

            model = view._replyEditorViews[2].model;
            expect(model.get('anchorPrefix')).toBe('footer-reply');
            expect(model.get('contextID')).toBe(null);
            expect(model.get('contextType')).toBe('body_bottom');
            expect(model.get('hasDraft')).toBe(false);

            expect(view._replyDraftsCount).toBe(1);
        });

        it('Draft banner when draft comment exists', function() {
            expect(view.trigger)
                .toHaveBeenCalledWith('hasDraftChanged', true);
        });

        describe('reviewReply changes on', function() {
            it('Discard', function() {
                spyOn(view, '_setupNewReply');

                spyOn(reviewReply, 'discardIfEmpty').and.callFake(
                    (options, context) => options.success.call(context));

                reviewReply.trigger('destroyed');

                expect(view._setupNewReply).toHaveBeenCalled();
            });

            it('Publish', function() {
                spyOn(view, '_setupNewReply');

                /*
                 * Avoid any of the steps in saving the replies. This
                 * short-circuits a lot of the logic, but for the purposes
                 * of this test, it's sufficient.
                 */
                spyOn(RB.BaseResource.prototype, 'ready');

                /*
                 * Save each editor, so the necessary state is available for
                 * the publish operation.
                 */
                view._replyEditors.forEach(editor => editor.save());
                reviewReply.trigger('published');

                expect(view._setupNewReply).toHaveBeenCalled();
            });
        });

        describe('When draft deleted', function() {
            describe('With last one', function() {
                it('Draft banner hidden', function() {
                    const editor = view._replyEditors[0];
                    expect(editor.get('hasDraft')).toBe(true);
                    expect(view._replyDraftsCount).toBe(1);
                    expect(view._draftBannerShown).toBe(true);

                    editor.set('hasDraft', false);
                    expect(view._replyDraftsCount).toBe(0);
                    expect(view._draftBannerShown).toBe(false);
                });
            });

            describe('With more remaining', function() {
                it('Draft banner stays visible', function() {
                    view._replyEditors[1].set('hasDraft', true);

                    const editor = view._replyEditors[0];
                    expect(editor.get('hasDraft')).toBe(true);

                    expect(view._replyDraftsCount).toBe(2);
                    expect(view._draftBannerShown).toBe(true);

                    editor.set('hasDraft', false);
                    expect(view._replyDraftsCount).toBe(1);
                    expect(view._draftBannerShown).toBe(true);
                });
            });
        });

        describe('When reviewReply changes', function() {
            it('Signals connected', function() {
                spyOn(view, 'listenTo').and.callThrough();

                view._setupNewReply(new RB.ReviewReply());

                expect(view.listenTo.calls.argsFor(0)[1])
                    .toBe('destroyed published');
            });

            it('Signals disconnected from old reviewReply', function() {
                spyOn(view, 'stopListening').and.callThrough();

                view._setupNewReply();

                expect(view.stopListening).toHaveBeenCalledWith(reviewReply);
            });

            it('Hide draft banner signal emitted', function() {
                view._setupNewReply();
                expect(view.trigger).toHaveBeenCalledWith('hasDraftChanged',
                                                          false);
            });

            it('Editors updated', function() {
                view._setupNewReply();

                view._replyEditors.forEach(editor =>
                    expect(editor.get('reviewReply')).toBe(view._reviewReply));
            });
        });
    });
});
