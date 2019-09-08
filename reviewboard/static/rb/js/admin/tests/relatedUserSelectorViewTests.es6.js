suite('rb/admin/views/relatedUserSelectorView', function() {
    describe('Rendering', function() {
        it('when empty', function() {
            let view = new RB.RelatedUserSelectorView({
                $input: $('<input id="id_people" type="hidden">'),
                initialOptions: [],
                useAvatars: true,
                multivalued: true
            });
            expect(view.options.useAvatars).toBe(true);
            expect(view.options.multivalued).toBe(true);
            view.render();

            expect(view.$el.find('.related-object-selected li').length)
                .toBe(0);
        });
    });

    describe('Rendering', function() {
        it('with inital options', function() {
            let view = new RB.RelatedUserSelectorView({
                $input: $('<input id="id_people" type="hidden">'),
                initialOptions: [{
                    username: 'admin',
                    fullname: 'Admin User',
                    id: 1,
                    avatarHTML: {
                        '20': '<div class="avatar" alt="Admin User"></div>',
                    },
                }, {
                    username: 'doc',
                    fullname: "Doc Dwarf",
                    id: 2,
                    avatarHTML: {
                        '20': '<div class="avatar" alt="Doc Dwarf"></div>',
                    },
                }, {
                    username: 'dopey',
                    fullname: 'Dopey Dwarf',
                    id: 3,
                    avatarHTML: {
                        '20': '<div class="avatar" alt="Dopey Dwarf"></div>',
                    },
                }],
                useAvatars: true,
                multivalued: true,
            });
            view.render();
            expect(view.options.useAvatars).toBe(true);
            expect(view.options.multivalued).toBe(true);

            expect(view.$el.find('.related-object-selected li').length)
                .toBe(3);
            expect(view.$el.siblings('#id_people').val()).toBe('');
            /* The input element value should be empty, since the widget will
               not fill in the values from the objects if the objects are
               passed through initialOptions. */
            expect(view._selectedIDs.size).toBe(3);
        });
    });

    describe('Select item', function() {
        let view;

        beforeEach(function(done) {
            $testsScratch.append('<input id="id_people" type="hidden">');
            view = new RB.RelatedUserSelectorView({
                $input: $('#id_people'),
                initialOptions: [],
                useAvatars: true,
                multivalued: true
            });
            view.render();

            /* These are the fake users, that will be displayed in the
               dropdown */
            spyOn(view, 'loadOptions').and.callFake(function(query, callback) {
                callback([{
                    avatarHTML: {
                        '20': '<div class="avatar" alt="Admin User"></div>',
                    },
                    fullname: 'Admin User',
                    id: 1,
                    username: 'admin',
                }, {
                    avatarHTML: {
                        '20': '<div class="avatar" alt="Doc Dwarf"></div>',
                    },
                    fullname: 'Doc Dwarf',
                    id: 2,
                    username: 'doc',
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
            $("div[data-value='admin']").click();
            $("div[data-value='doc']").click();
            expect(view.$el.siblings('#id_people').val()).toBe('1,2');
            done();
        });
    });


});