suite('rb/admin/views/relatedGroupSelectorView', function() {
    describe('Rendering', function() {
        it('when empty', function() {
            let view = new RB.RelatedGroupSelectorView({
                $input: $('<input id="id_groups" type="hidden">'),
                initialOptions: [],
                multivalued: true,
                inviteOnly: false,
            });
            expect(view.options.multivalued).toBe(true);
            expect(view.options.inviteOnly).toBe(false);
            view.render();

            expect(view.$el.find('.related-object-selected li').length)
                .toBe(0);

        });
    });

    describe('Rendering', function() {
        it('with inital options', function() {
            let view = new RB.RelatedGroupSelectorView({
                $input: $('<input id="id_groups" type="hidden">'),
                initialOptions: [{
                    id: 1,
                    display_name: "Test Repository 1",
                    name: "test_repo_1",
                    invite_only: false,
                }, {
                    id: 2,
                    display_name: "Test Repository 2",
                    name: "test_repo_2",
                    invite_only: true,
                }],
                multivalued: true,
                inviteOnly: true,
            });
            view.render();
            expect(view.options.multivalued).toBe(true);
            expect(view.options.inviteOnly).toBe(true);

            expect(view.$el.find('.related-object-selected li').length)
                .toBe(2);
            expect(view.$el.siblings('#id_groups').val()).toBe('');
            /* The input element value should be empty, since the widget will
               not fill in the values from the objects if the objects are
               passed through initialOptions. */
            expect(view._selectedIDs.size).toBe(2);

        });
    });

    describe('Select item', function() {
        let view;

        beforeEach(function(done) {
            $testsScratch.append('<input id="id_groups" type="hidden">');
            view = new RB.RelatedGroupSelectorView({
                $input: $('#id_groups'),
                initialOptions: [],
                multivalued: true
            });
            view.render();

            /* These are the fake users, that will be displayed in the
               dropdown */
            spyOn(view, 'loadOptions').and.callFake(function(query, callback) {
                callback([{
                    id: 1,
                    display_name: "Test Repository 1",
                    name: "test_repo_1",
                    invite_only: false,
                }, {
                    id: 2,
                    display_name: "Test Repository 2",
                    name: "test_repo_2",
                    invite_only: true,
                }]);
            });

            $('select')[0].selectize.focus();
            /* The focus() method is being called asynchronously, so it
              doesn't actually call the loadOptions() method here
              instantly. That's why I use setTimeout to wait for it to
              finish. */
            setTimeout(function() {
                $testsScratch.find('div .selectize-input.items.not-full input').click();
                done();
            }, 4000);
            /* I probably shouldn't be doing this, but I
            don't know how else to get it to work. */
        });

        it('from dropdown', function(done) {
            expect(view.loadOptions).toHaveBeenCalled();
            $("div[data-value='test_repo_1']").click();
            $("div[data-value='test_repo_2']").click();
            expect(view.$el.siblings('#id_groups').val()).toBe('1,2');
            done();
        });
    });


});