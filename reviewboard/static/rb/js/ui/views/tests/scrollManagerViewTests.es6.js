suite('rb/ui/views/ScrollManagerView', function() {
    function makeElement(dimensions={}) {
        const scratchOffset = $testsScratch.offset();

        return $('<div/>')
            .css({
                position: 'absolute',
                left: -scratchOffset.left + (dimensions.left || 0),
                top: -scratchOffset.top + (dimensions.top || 0),
                width: dimensions.width || 20,
                height: dimensions.height || 20,
            })
            .appendTo($testsScratch);
    }

    let scrollManager;

    beforeEach(function() {
        scrollManager = new RB.ScrollManagerView();
        scrollManager.window = {
            pageXOffset: 0,
            pageYOffset: 0,

            scrollTo(x, y) {
                this.pageXOffset = x;
                this.pageYOffset = y;
            },

            requestAnimationFrame(cb) {
                cb();
            },
        };
    });

    describe('scrollToPosition', function() {
        it('Without scroll offset', function() {
            scrollManager.scrollToPosition(100);

            expect(Math.round(scrollManager.window.pageYOffset)).toBe(100);
        });

        it('With scroll offset', function() {
            scrollManager.scrollYOffset = 40;
            scrollManager.scrollToPosition(100);

            expect(Math.round(scrollManager.window.pageYOffset)).toBe(60);
        });
    });

    describe('scrollToElement', function() {
        let $el;

        beforeEach(function() {
            $el = makeElement({top: 50});
        });

        it('Without scroll offset', function() {
            scrollManager.scrollToElement($el);

            expect(Math.round(scrollManager.window.pageYOffset)).toBe(50);
        });

        it('With scroll offset', function() {
            scrollManager.scrollYOffset = 40;
            scrollManager.scrollToElement($el);

            expect(Math.round(scrollManager.window.pageYOffset)).toBe(10);
        });
    });

    describe('markUpdated', function() {
        let $el;

        beforeEach(function() {
            $el = makeElement({top: 50});
        });

        it('First in a batch', function() {
            scrollManager.window.pageYOffset = 100;

            expect(scrollManager._oldScrollY).toBe(null);

            scrollManager.markForUpdate($el);

            const pendingElement = scrollManager._pendingElements.get($el[0]);
            expect(Math.round(pendingElement.oldHeight)).toEqual(20);
            expect(Math.round(pendingElement.oldOffset.top)).toEqual(50);
            expect(Math.round(pendingElement.oldOffset.left)).toEqual(0);
            expect(scrollManager._oldScrollY).toBe(100);
        });

        it('Subsequent entries', function() {
            scrollManager._oldScrollY = 100;
            scrollManager.window.pageYOffset = 200;

            scrollManager.markForUpdate($el);

            const pendingElement = scrollManager._pendingElements.get($el[0]);
            expect(Math.round(pendingElement.oldHeight)).toEqual(20);
            expect(Math.round(pendingElement.oldOffset.top)).toEqual(50);
            expect(Math.round(pendingElement.oldOffset.left)).toEqual(0);
            expect(scrollManager._oldScrollY).toBe(100);
        });
    });

    describe('markUpdated', function() {
        let $el;

        beforeEach(function() {
            $el = makeElement({top: 50});
        });

        it('Stores correct state', function() {
            /* Disable the actual updates for this test. */
            spyOn(scrollManager.window, 'requestAnimationFrame');

            scrollManager.markForUpdate($el);
            $el.height(40);
            $el.css('top', parseInt($el.css('top'), 10) - 10);
            scrollManager.markUpdated($el);

            const el = $el[0];

            expect(scrollManager._pendingElements.get(el)).toBe(undefined);

            const element = scrollManager._elements.get(el);
            expect(Math.round(element.oldHeight)).toEqual(20);
            expect(Math.round(element.oldOffset.top)).toEqual(50);
            expect(Math.round(element.oldOffset.left)).toEqual(0);
            expect(Math.round(element.newHeight)).toEqual(40);
            expect(Math.round(element.newOffset.top)).toEqual(40);
            expect(Math.round(element.newOffset.left)).toEqual(0);

            expect(scrollManager.window.requestAnimationFrame)
                .toHaveBeenCalled();
        });
    });

    describe('Scroll updates', function() {
        beforeEach(function() {
            spyOn(scrollManager.window, 'requestAnimationFrame');

            scrollManager.window.pageYOffset = 200;
        });

        it('Includes updates before scroll position', function() {
            const $el1 = makeElement({top: 10});
            const $el2 = makeElement({top: 60});
            const $el3 = makeElement({top: 70});

            /* Grow by 50px. */
            scrollManager.markForUpdate($el1);
            $el1.height(70);
            scrollManager.markUpdated($el1);

            /* Shrink by 10px. */
            scrollManager.markForUpdate($el2);
            $el2.height(10);
            scrollManager.markUpdated($el2);

            /* Move up 5px. */
            scrollManager.markForUpdate($el3);
            $el3.css('top', parseInt($el3.css('top'), 10) - 5);
            scrollManager.markUpdated($el3);

            scrollManager._updateScrollPos();

            expect(Math.round(scrollManager.window.pageYOffset)).toBe(235);
        });

        it('Ignores updates after scroll position', function() {
            const $el1 = makeElement({top: 10});
            const $el2 = makeElement({top: scrollManager.window.pageYOffset});
            const $el3 = makeElement({top: 500});

            scrollManager.markForUpdate($el1);
            $el1.height(30);
            scrollManager.markUpdated($el1);

            scrollManager.markForUpdate($el2);
            $el2.height(90);
            scrollManager.markUpdated($el2);

            scrollManager.markForUpdate($el3);
            $el3.height(1000);
            scrollManager.markUpdated($el3);

            scrollManager._updateScrollPos();

            expect(scrollManager.window.pageYOffset).toBe(210);
        });
    });
});
