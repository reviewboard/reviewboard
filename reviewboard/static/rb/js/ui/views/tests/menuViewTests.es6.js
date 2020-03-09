suite('rb/ui/views/MenuView', function() {
    const ANIMATE_WAIT_MS = 300;

    describe('Rendering', function() {
        it('Standard menus', function() {
            const view = new RB.MenuView();
            view.render().$el.appendTo($testsScratch);

            expect(view.el.id).toBe(view.id);
            expect(view.el.id).toMatch(/^__rb-menu\d+/);
            expect(view.el).toHaveClass('rb-c-menu');
            expect(view.el).not.toHaveClass('rb-c-button-group');
            expect(view.el).not.toHaveClass('-is-vertical');
            expect(view.el.tabIndex).toBe(-1);
            expect(view.$el.attr('role')).toBe('menu');
            expect(view.$el.css('display')).toBe('block');
            expect(view.$el.css('visibility')).toBe('hidden');
            expect(view.$el.css('opacity')).toBe('0');
        });

        it('Button menus', function() {
            const view = new RB.MenuView({
                type: RB.MenuView.TYPE_BUTTON_MENU,
            });
            view.render().$el.appendTo($testsScratch);

            expect(view.el.id).toBe(view.id);
            expect(view.el.id).toMatch(/^__rb-menu\d+/);
            expect(view.el).toHaveClass('rb-c-menu');
            expect(view.el).toHaveClass('rb-c-button-group');
            expect(view.el).toHaveClass('-is-vertical');
            expect(view.el.tabIndex).toBe(-1);
            expect(view.$el.attr('role')).toBe('menu');
            expect(view.$el.css('display')).toBe('block');
            expect(view.$el.css('visibility')).toBe('hidden');
            expect(view.$el.css('opacity')).toBe('0');
        });

        it('With ariaLabelledBy', function() {
            const view = new RB.MenuView({
                type: RB.MenuView.TYPE_BUTTON_MENU,
                ariaLabelledBy: 'abc123',
                ariaLabel: 'unused label',
            });
            view.render().$el.appendTo($testsScratch);

            expect(view.$el.attr('aria-label')).toBeUndefined();
            expect(view.$el.attr('aria-labelledby')).toBe('abc123');
        });

        it('With ariaLabel', function() {
            const view = new RB.MenuView({
                type: RB.MenuView.TYPE_BUTTON_MENU,
                ariaLabel: 'ARIA label',
            });
            view.render();

            expect(view.$el.attr('aria-label')).toBe('ARIA label');
            expect(view.$el.attr('aria-labelledby')).toBeUndefined();
        });

        it('With $controller', function() {
            const $controller = $('<div>');

            const view = new RB.MenuView({
                type: RB.MenuView.TYPE_BUTTON_MENU,
                $controller: $controller,
            });
            view.render();

            expect(view.el.id).toBe(view.id);
            expect(view.el.id).toMatch(/^__rb-menu\d+/);
            expect($controller.attr('aria-controls')).toBe(view.el.id);
            expect($controller.attr('aria-expanded')).toBe('false');
            expect($controller.attr('aria-haspopup')).toBe('true');
        });
    });

    describe('Methods', function() {
        describe('addItem', function() {
            it('For standard menus', function() {
                const view = new RB.MenuView();
                view.render();

                const $menuItem = view.addItem();
                const menuItem = $menuItem[0];

                expect(menuItem.tagName).toBe('DIV');
                expect(menuItem.tabIndex).toBe(-1);
                expect(menuItem).toHaveClass('rb-c-menu__item');
                expect(menuItem).not.toHaveClass('rb-c-button');
                expect($menuItem.attr('role')).toBe('menuitem');

                const $children = view.$el.children();
                expect($children.length).toBe(1);
                expect($children[0]).toBe(menuItem);
            });

            it('For button menus', function() {
                const view = new RB.MenuView({
                    type: RB.MenuView.TYPE_BUTTON_MENU,
                });
                view.render();

                const $menuItem = view.addItem();
                const menuItem = $menuItem[0];

                expect(menuItem.tagName).toBe('BUTTON');
                expect(menuItem.tabIndex).toBe(-1);
                expect(menuItem).toHaveClass('rb-c-menu__item');
                expect(menuItem).toHaveClass('rb-c-button');
                expect($menuItem.attr('type')).toBe('button');
                expect($menuItem.attr('role')).toBe('menuitem');

                const $children = view.$el.children();
                expect($children.length).toBe(1);
                expect($children[0]).toBe(menuItem);
            });

            it('With text', function() {
                const view = new RB.MenuView({
                    type: RB.MenuView.TYPE_BUTTON_MENU,
                });
                view.render();

                const $menuItem = view.addItem({
                    text: 'This is a test',
                });
                expect($menuItem.text()).toBe('This is a test');
            });
        });

        describe('open', function() {
            let $controller;
            let view;

            beforeEach(function() {
                $controller = $('<div>')
                    .appendTo($testsScratch);

                view = new RB.MenuView({
                    $controller: $controller,
                });
                view.render().$el.appendTo($testsScratch);

                expect(view.$el.css('display')).toBe('block');
                expect(view.$el.css('visibility')).toBe('hidden');
                expect(view.$el.css('opacity')).toBe('0');

                spyOn(view, 'trigger').and.callThrough();
            });

            it('Default behavior', function(done) {
                view.open();

                _.delay(() => {
                    expect(view.isOpen).toBeTrue();
                    expect(view.el).toHaveClass('-is-open');
                    expect(view.el).not.toHaveClass('js-no-animation');
                    expect(view.$el.css('display')).toBe('block');
                    expect(view.$el.css('visibility')).toBe('visible');
                    expect(view.$el.css('opacity')).toBe('1');
                    expect($controller.attr('aria-expanded')).toBe('true');

                    done();
                }, ANIMATE_WAIT_MS);
            });

            it('With animate=false', function(done) {
                view.open({
                    animate: false,
                });

                expect(view.isOpen).toBeTrue();
                expect(view.el).toHaveClass('-is-open');
                expect(view.el).toHaveClass('js-no-animation');
                expect(view.$el.css('display')).toBe('block');
                expect(view.$el.css('visibility')).toBe('visible');
                expect(view.$el.css('opacity')).toBe('1');
                expect(view.trigger).toHaveBeenCalledWith('opening');
                expect(view.trigger).toHaveBeenCalledWith('opened');
                expect($controller.attr('aria-expanded')).toBe('true');

                _.defer(() => {
                    expect(view.el).not.toHaveClass('js-no-animation');
                    done();
                });
            });
        });

        describe('close', function() {
            let $controller;
            let view;

            beforeEach(function() {
                $controller = $('<div aria-expanded="true">')
                    .appendTo($testsScratch);

                view = new RB.MenuView({
                    $controller: $controller,
                });
                view.render().$el.appendTo($testsScratch);

                view.isOpen = true;
                view.$el.addClass('-is-open');

                expect(view.$el.css('display')).toBe('block');
                expect(view.$el.css('visibility')).toBe('visible');
                expect(view.$el.css('opacity')).toBe('1');

                spyOn(view, 'trigger').and.callThrough();
            });

            it('Default behavior', function(done) {
                view.close();

                _.delay(() => {
                    expect(view.isOpen).toBeFalse();
                    expect(view.el).not.toHaveClass('-is-open');
                    expect(view.el).not.toHaveClass('js-no-animation');
                    expect(view.$el.css('display')).toBe('block');
                    expect(view.$el.css('visibility')).toBe('hidden');
                    expect(view.$el.css('opacity')).toBe('0');
                    expect($controller.attr('aria-expanded')).toBe('false');
                    done();
                }, ANIMATE_WAIT_MS);
            });

            it('With animate=false', function(done) {
                view.close({
                    animate: false,
                });

                expect(view.isOpen).toBeFalse();
                expect(view.el).toHaveClass('js-no-animation');
                expect(view.el).not.toHaveClass('-is-open');
                expect(view.$el.css('display')).toBe('block');
                expect(view.$el.css('visibility')).toBe('hidden');
                expect(view.$el.css('opacity')).toBe('0');
                expect(view.trigger).toHaveBeenCalledWith('closing');
                expect(view.trigger).toHaveBeenCalledWith('closed');
                expect($controller.attr('aria-expanded')).toBe('false');

                _.defer(() => {
                    expect(view.el).not.toHaveClass('js-no-animation');
                    done();
                });
            });
        });

        it('focusFirstItem', function() {
            const view = new RB.MenuView();
            view.render().$el.appendTo($testsScratch);
            view.open({
                animate: false,
            });

            const itemEl = view.addItem()[0];
            view.addItem();
            view.addItem();

            /*
             * We'll be spying on focus() instead of checking the resulting
             * focused element in order to work around issues with the
             * browser's developer tools console having focus during unit
             * tests, causing our element to never actually gain focus.
             */
            spyOn(itemEl, 'focus');

            view.focusFirstItem();

            expect(itemEl.focus).toHaveBeenCalled();
            expect(view._activeItemIndex).toBe(0);
        });

        it('focusLastItem', function() {
            const view = new RB.MenuView();
            view.render().$el.appendTo($testsScratch);
            view.open({
                animate: false,
            });

            view.addItem();
            view.addItem();
            const itemEl = view.addItem()[0];

            /*
             * We'll be spying on focus() instead of checking the resulting
             * focused element in order to work around issues with the
             * browser's developer tools console having focus during unit
             * tests, causing our element to never actually gain focus.
             */
            spyOn(itemEl, 'focus');

            view.focusLastItem();

            expect(itemEl.focus).toHaveBeenCalled();
            expect(view._activeItemIndex).toBe(2);
        });
    });

    describe('Keyboard Accessibility', function() {
        let $controller;
        let $item1;
        let $item2;
        let $item3;
        let view;

        function sendKeyDown(keyCode) {
            view.$el.trigger($.Event('keydown', {
                which: keyCode,
            }));
        }

        beforeEach(function() {
            $controller = $('<div>')
                .appendTo($testsScratch);

            view = new RB.MenuView({
                $controller: $controller,
            });
            view.render().$el.appendTo($testsScratch);

            $item1 = view.addItem();
            $item2 = view.addItem();
            $item3 = view.addItem();

            view.open({
                animate: false,
            });
            view._focusItem(1);

            spyOn(view, 'trigger').and.callThrough();
        });

        it('Enter key activates item', function() {
            const spy = jasmine.createSpy();

            $item2.on('click', spy);

            sendKeyDown($.ui.keyCode.ENTER);

            expect(spy).toHaveBeenCalled();
        });

        it('Escape key closes menu', function() {
            spyOn($controller[0], 'focus');

            sendKeyDown($.ui.keyCode.ESCAPE);

            expect(view.el).not.toHaveClass('-is-open');
            expect($controller[0].focus).toHaveBeenCalled();
        });

        it('Tab key closes menu', function() {
            spyOn($controller[0], 'focus');

            sendKeyDown($.ui.keyCode.TAB);

            expect(view.el).not.toHaveClass('-is-open');
            expect($controller[0].focus).toHaveBeenCalled();
        });

        it('Up key moves focus up', function() {
            spyOn(view, '_focusItem').and.callThrough();

            sendKeyDown($.ui.keyCode.UP);
            expect(view._focusItem).toHaveBeenCalledWith(0);

            /* It should now wrap. */
            sendKeyDown($.ui.keyCode.UP);
            expect(view._focusItem).toHaveBeenCalledWith(2);
        });

        it('Down key moves focus up', function() {
            spyOn(view, '_focusItem').and.callThrough();

            sendKeyDown($.ui.keyCode.DOWN);
            expect(view._focusItem).toHaveBeenCalledWith(2);

            /* It should now wrap. */
            sendKeyDown($.ui.keyCode.DOWN);
            expect(view._focusItem).toHaveBeenCalledWith(0);
        });

        it('Home key moves focus to top', function() {
            spyOn(view, '_focusItem').and.callThrough();

            sendKeyDown($.ui.keyCode.HOME);
            expect(view._focusItem).toHaveBeenCalledWith(0);
        });

        it('Page Up key moves focus to top', function() {
            spyOn(view, '_focusItem').and.callThrough();

            sendKeyDown($.ui.keyCode.PAGE_UP);
            expect(view._focusItem).toHaveBeenCalledWith(0);
        });

        it('End key moves focus to bottom', function() {
            spyOn(view, '_focusItem').and.callThrough();

            sendKeyDown($.ui.keyCode.END);
            expect(view._focusItem).toHaveBeenCalledWith(2);
        });

        it('Page Down key moves focus to bottom', function() {
            spyOn(view, '_focusItem').and.callThrough();

            sendKeyDown($.ui.keyCode.PAGE_DOWN);
            expect(view._focusItem).toHaveBeenCalledWith(2);
        });
    });
});
