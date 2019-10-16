suite('rb/ui/views/DrawerView', function() {
    let $body;
    let drawerView;

    beforeEach(function() {
        $body = $(document.body);

        drawerView = new RB.DrawerView();
        drawerView.render();
    });

    afterEach(function() {
        $body.removeClass('js-rb-c-drawer-is-shown');
    });

    describe('Operations', function() {
        it('show', function() {
            const onVisibilityChanged =
                jasmine.createSpy('onVisibilityChanged');

            drawerView.on('visibilityChanged', onVisibilityChanged);
            drawerView.show();

            expect(drawerView.isVisible).toBe(true);
            expect($body.hasClass('js-rb-c-drawer-is-shown')).toBe(true);
            expect(onVisibilityChanged).toHaveBeenCalledWith(true);
        });

        it('hide', function() {
            const onVisibilityChanged =
                jasmine.createSpy('onVisibilityChanged');

            $body.addClass('js-rb-c-drawer-is-shown');

            drawerView.on('visibilityChanged', onVisibilityChanged);
            drawerView.hide();

            expect(drawerView.isVisible).toBe(false);
            expect($body.hasClass('js-rb-c-drawer-is-shown')).toBe(false);
            expect(onVisibilityChanged).toHaveBeenCalledWith(false);
        });
    });
});
