suite('rb/ui/views/MenuButtonView', function() {
    describe('Rendering', function() {
        it('With primary button', function() {
            const view = new RB.MenuButtonView({
                ariaMenuLabel: 'Test ARIA label',
                menuItems: [
                    {text: 'Item 1'},
                    {text: 'Item 2'},
                    {text: 'Item 3'},
                ],
                onPrimaryButtonClick: () => {},
                text: 'Button label',
            });
            view.render();

            expect(view.el).toHaveClass('rb-c-menu-button');
            expect(view.$el.attr('role')).toBe('group');
            expect(view.$primaryButton.length).toBe(1);

            const $primaryButton = view.$('.rb-c-menu-button__primary');
            expect($primaryButton.length).toBe(1);

            const $toggleButton = view.$('.rb-c-menu-button__toggle');
            expect($toggleButton.length).toBe(1);
            expect($toggleButton[0].id)
                .toBe(view.menu.$el.attr('aria-labelledby'));
            expect($toggleButton.attr('aria-label')).toBe('Test ARIA label');
            expect($toggleButton.children()[0])
                .toHaveClass('rb-icon-dropdown-arrow');

            expect(view.menu.el.children.length).toBe(3);
        });

        it('Without primary button', function() {
            const view = new RB.MenuButtonView({
                ariaMenuLabel: 'Test ARIA label',
                menuItems: [
                    {text: 'Item 1'},
                    {text: 'Item 2'},
                ],
                text: 'Button label',
            });
            view.render();

            expect(view.el).toHaveClass('rb-c-menu-button');
            expect(view.$el.attr('role')).toBe('group');
            expect(view.$primaryButton).toBeNull();

            const $primaryButton = view.$('.rb-c-menu-button__primary');
            expect($primaryButton.length).toBe(0);

            const $toggleButton = view.$('.rb-c-menu-button__toggle');
            expect($toggleButton.length).toBe(1);
            expect($toggleButton[0].id)
                .toBe(view.menu.$el.attr('aria-labelledby'));
            expect($toggleButton.attr('aria-label')).toBeUndefined();
            expect($toggleButton.text().trim()).toBe('Button label');
            expect($toggleButton.children()[0])
                .toHaveClass('rb-icon-dropdown-arrow');

            expect(view.menu.el.children.length).toBe(2);
        });
    });

    describe('Events', function() {
        let view;

        function sendDropDownButtonEvent(name, options) {
            view._$dropDownButton.trigger($.Event(name, options));
        }

        function sendKeyDown(keyCode) {
            sendDropDownButtonEvent('keydown', {
                which: keyCode,
            });
        }

        beforeEach(function() {
            view = new RB.MenuButtonView();
            view.render();

            /* Don't let this override any state we set. */
            spyOn(view, '_updateMenuPosition');
        });

        describe('keydown', function() {
            function openMenuTests(keyCode) {
                it('With openDirection=up', function() {
                    view._openDirection = 'up';
                    spyOn(view.menu, 'focusLastItem');

                    sendKeyDown(keyCode);

                    expect(view.menu.isOpen).toBeTrue();
                    expect(view.menu.focusLastItem).toHaveBeenCalled();
                });

                it('With openDirection=down', function() {
                    view._openDirection = 'down';
                    spyOn(view.menu, 'focusFirstItem');

                    sendKeyDown(keyCode);

                    expect(view.menu.isOpen).toBeTrue();
                    expect(view.menu.focusFirstItem).toHaveBeenCalled();
                });
            }

            describe('Return key opens menu', function() {
                openMenuTests($.ui.keyCode.RETURN);
            });

            describe('Space key opens menu', function() {
                openMenuTests($.ui.keyCode.SPACE);
            });

            describe('Down key opens menu', function() {
                openMenuTests($.ui.keyCode.DOWN);
            });

            describe('Up key opens menu', function() {
                openMenuTests($.ui.keyCode.UP);
            });

            it('Escape key closes menu', function() {
                view.menu.open({
                    animate: false,
                });
                expect(view.menu.isOpen).toBeTrue();

                sendKeyDown($.ui.keyCode.ESCAPE);

                expect(view.menu.isOpen).toBeFalse();
            });
        });

        it('focusout closes menu', function() {
            view.menu.open({
                animate: false,
            });

            expect(view.menu.isOpen).toBeTrue();

            sendDropDownButtonEvent('focusout', {
                relatedTarget: $testsScratch[0],
            });

            expect(view.menu.isOpen).toBeFalse();
        });
    });
});
