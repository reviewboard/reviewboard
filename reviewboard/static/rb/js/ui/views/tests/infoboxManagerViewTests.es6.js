suite('rb/ui/views/InfoboxManagerView', () => {
    const DummyInfoboxView = RB.BaseInfoboxView.extend({
        infoboxID: 'dummy-infobox',
    });

    let infoboxManagerView;

    beforeEach(() => {
        infoboxManagerView = RB.InfoboxManagerView.getInstance();

        spyOn(infoboxManagerView, '_fetchInfoboxContents')
            .and.callFake((url, onDone) => {
                expect(url).toBe('/foo/infobox/');
                onDone('<strong>Hi!</strong>');
            });
    });

    afterEach(() => {
        infoboxManagerView.remove();
        RB.InfoboxManagerView._instance = null;
    });

    describe('addTargets', () => {
        let $el1;
        let $el2;
        let $els;

        beforeEach(() => {
            $el1 = $('<div/>');
            $el2 = $('<div/>');
            $els = $([$el1[0], $el2[0]]);
        });

        it('Registers new targets', () => {
            infoboxManagerView.addTargets(DummyInfoboxView, $els);

            expect($el1.data('has-infobox')).toBe(true);
            expect($el2.data('has-infobox')).toBe(true);
        });

        it('Registers event handlers', () => {
            spyOn(infoboxManagerView, '_onTargetMouseEnter');
            spyOn(infoboxManagerView, '_onMouseLeave');

            infoboxManagerView.addTargets(DummyInfoboxView, $els);

            $el1.triggerHandler('mouseenter');
            expect(infoboxManagerView._onTargetMouseEnter).toHaveBeenCalled();

            $el1.triggerHandler('mouseleave');
            expect(infoboxManagerView._onMouseLeave).toHaveBeenCalled();
        });

        it('Skips already-registered targets', () => {
            spyOn(infoboxManagerView, '_onTargetMouseEnter');

            infoboxManagerView.addTargets(DummyInfoboxView, $els);
            infoboxManagerView.addTargets(DummyInfoboxView, $els);

            $el1.triggerHandler('mouseenter');
            expect(infoboxManagerView._onTargetMouseEnter.calls.count())
                .toBe(1);
        });
    });

    describe('getOrCreateInfobox', () => {
        it('Caches infobox views', () => {
            const infoboxView1 = infoboxManagerView.getOrCreateInfobox(
                DummyInfoboxView);
            const infoboxView2 = infoboxManagerView.getOrCreateInfobox(
                DummyInfoboxView);

            expect(infoboxView1.cid).toBe(infoboxView2.cid);
        });

        it('Starts infobox hidden', () => {
            const infoboxView = infoboxManagerView.getOrCreateInfobox(
                DummyInfoboxView);

            expect(infoboxView.$el.is(':visible')).toBe(false);
        });

        it('Registers events', () => {
            spyOn(infoboxManagerView, '_onInfoboxMouseEnter');
            spyOn(infoboxManagerView, '_onMouseLeave');

            const infoboxView = infoboxManagerView.getOrCreateInfobox(
                DummyInfoboxView);

            infoboxView.$el.triggerHandler('mouseenter');
            expect(infoboxManagerView._onInfoboxMouseEnter).toHaveBeenCalled();

            infoboxView.$el.triggerHandler('mouseleave');
            expect(infoboxManagerView._onMouseLeave).toHaveBeenCalled();
        });
    });

    describe('setPositioning', () => {
        it('Overrides default position', () => {
            infoboxManagerView.setPositioning(DummyInfoboxView, {
                side: 'b',
                foo: 'bar',
            });

            const infoboxView = infoboxManagerView.getOrCreateInfobox(
                DummyInfoboxView);
            expect(infoboxView.positioning).toEqual({
                side: 'b',
                foo: 'bar',
            });
        });
    });

    describe('Target Events', () => {
        let $el;

        beforeEach(() => {
            spyOn(window, 'setTimeout').and.callFake(cb => cb());

            $el = $('<a href="/foo/" />');
            infoboxManagerView.addTargets(DummyInfoboxView, $el);
        });

        describe('mouseenter', () => {
            it('First time for target', () => {
                $el.triggerHandler('mouseenter');

                const infoboxView = infoboxManagerView.getOrCreateInfobox(
                    DummyInfoboxView);
                expect(infoboxView.$el.html()).toBe('<strong>Hi!</strong>');
                expect(infoboxView.$el.is(':visible')).toBe(true);
            });

            it('Subsequent time for target (cached data)', () => {
                const infoboxView = infoboxManagerView.getOrCreateInfobox(
                    DummyInfoboxView);

                spyOn(infoboxView, 'setContents').and.callThrough();
                spyOn(infoboxManagerView, '_showInfobox')
                    .and.callThrough();

                infoboxManagerView._cache['/foo/infobox/'] = 'Old HTML';

                $el.triggerHandler('mouseenter');

                expect(infoboxView.$el.html()).toBe('<strong>Hi!</strong>');
                expect(infoboxView.$el.is(':visible')).toBe(true);
                expect(infoboxManagerView._showInfobox.calls.count())
                    .toBe(1);
                expect(infoboxView.setContents.calls.count()).toBe(2);
            });
        });

        describe('mouseleave', () => {
            beforeEach(() => {
                $el.triggerHandler('mouseenter');
            });

            it('Cancels showing infobox', () => {
                infoboxManagerView._showTimeout = 123;

                $el.triggerHandler('mouseleave');

                expect(infoboxManagerView._showTimeout).toBe(null);
            });

            it('Hides infobox', () => {
                const infoboxView = infoboxManagerView.getOrCreateInfobox(
                    DummyInfoboxView);
                infoboxManagerView._showTimeout = 123;

                expect(infoboxView.$el.is(':visible')).toBe(true);
                expect(infoboxManagerView._activeInfoboxView).not.toBe(null);

                $el.triggerHandler('mouseleave');

                expect(infoboxView.$el.is(':visible')).toBe(false);
                expect(infoboxManagerView._activeInfoboxView).toBe(null);
                expect(infoboxManagerView._showTimeout).toBe(null);
            });
        });
    });

    describe('Infobox Events', () => {
        let $el;

        beforeEach(() => {
            spyOn(window, 'setTimeout').and.callFake(cb => cb());

            $el = $('<a href="/foo/" />');
            infoboxManagerView.addTargets(DummyInfoboxView, $el);
        });

        describe('mouseenter', () => {
            it('Preserves infobox after leaving target', () => {
                const infoboxView = infoboxManagerView.getOrCreateInfobox(
                    DummyInfoboxView);

                /* Simulate hovering over a target. */
                $el.triggerHandler('mouseenter');
                expect(infoboxManagerView._activeInfoboxView)
                    .toBe(infoboxView);

                /*
                 * Restore the default behavior of the spy and simulate the
                 * mouse leaving the target.
                 */
                window.setTimeout.and.callThrough();
                $el.triggerHandler('mouseleave');

                expect(infoboxManagerView._hideTimeout).not.toBe(null);
                expect(infoboxManagerView._showTimeout).toBe(null);

                infoboxView.$el.triggerHandler('mouseenter');

                expect(infoboxView.$el.is(':visible')).toBe(true);
                expect(infoboxManagerView._showTimeout).toBe(null);
                expect(infoboxManagerView._hideTimeout).toBe(null);
            });
        });

        describe('mouseleave', () => {
            it('Hides infobox', () => {
                const infoboxView = infoboxManagerView.getOrCreateInfobox(
                    DummyInfoboxView);

                infoboxManagerView._showInfobox(infoboxView, $el);
                expect(infoboxView.$el.is(':visible')).toBe(true);
                expect(infoboxManagerView._activeInfoboxView)
                    .toBe(infoboxView);

                infoboxView.$el.triggerHandler('mouseleave');

                expect(infoboxView.$el.is(':visible')).toBe(false);
                expect(infoboxManagerView._activeInfoboxView).toBe(null);
                expect(infoboxManagerView._showTimeout).toBe(null);
            });
        });
    });
});
