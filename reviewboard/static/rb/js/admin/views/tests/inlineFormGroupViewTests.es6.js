suite('rb/admin/views/InlineFormGroupView', function() {
    const inlineTemplate = _.template(dedent`
        <div class="rb-c-admin-form-inline <%- classes || '' %>">
         <h3 class="rb-c-admin-form-inline__title">
          <span class="rb-c-admin-form-inline__title-prefix"></span>
          <span class="rb-c-admin-form-inline__title-object"></span>
          <span class="rb-c-admin-form-inline__title-index"></span>
          <span class="rb-c-admin-form-inline__actions">
           <span class="rb-c-admin-form-inline__delete-action"></span>
          </span>
         </h3>
         <fieldset>
          <div>
           <label for="myprefix-<%- index %>-foo"></label>
           <input id="myprefix-<%- index %>-foo"
                  name="myprefix-<%- index %>-foo">
          </div>
          <div>
           <label for="myprefix-<%- index %>-bar"></label>
           <input id="myprefix-<%- index %>-bar"
                  name="myprefix-<%- index %>-bar">
          </div>
         </fieldset>
        </div>
    `);

    const template = _.template(dedent`
        <div class="rb-c-admin-form-inline-group">
         <h2 class="rb-c-admin-form-inline-group__title"></h2>
         <div class="rb-c-admin-form-inline-group__inlines">
          <input type="hidden"
                 id="id_myprefix-TOTAL_FORMS"
                 name="myprefix-TOTAL_FORMS"
                 value="<%- totalForms %>">
          <input type="hidden"
                 id="id_myprefix-INITIAL_FORMS"
                 name="myprefix-INITIAL_FORMS"
                 value="<%- initialForms %>">
          <input type="hidden"
                 id="id_myprefix-MIN_NUM_FORMS"
                 name="myprefix-MIN_NUM_FORMS"
                 value="<%- minNumForms %>">
          <input type="hidden"
                 id="id_myprefix-MAX_NUM_FORMS"
                 name="myprefix-MAX_NUM_FORMS"
                 value="<%- maxNumForms %>">

          <% for (let i = 0; i < numInlines; i++) { %>
           <%= inlineTemplate({
               classes: '',
               index: i
           }) %>
          <% } %>
          <%= inlineTemplate({
              classes: '-is-template',
              index: '__prefix__'
          }) %>
         </div>
         <div class="rb-c-admin-form-inline-group__actions">
          <a href="#" class="rb-c-admin-form-inline-group__add-action"></a>
         </div>
        </div>
    `);

    let $el;
    let model;
    let view;

    function buildView(options) {
        $el =
            $(template(_.extend({
                initialForms: 0,
                inlineTemplate: inlineTemplate,
                maxNumForms: '',
                minNumForms: 0,
                numInlines: 0,
                totalForms: 0,
            }, options)))
            .appendTo($testsScratch);

        view = new RB.Admin.InlineFormGroupView({
            el: $el,
            model: model,
        });
        view.render();
    }

    beforeEach(function() {
        model = new RB.Admin.InlineFormGroup({
            prefix: 'myprefix',
        });
    });

    describe('State', function() {
        it('Populated on render', function() {
            buildView({
                numInlines: 2,
                initialForms: 2,
                minNumForms: 1,
                maxNumForms: 5,
                totalForms: 2,
            });

            expect($el.find('.rb-c-admin-form-inline').length).toBe(2);
            expect(view._$inlineTemplate.length).toBe(1);
            expect(view._$inlineTemplate.hasClass('-is-template')).toBeFalse();

            expect(model.get('initialInlines')).toBe(2);
            expect(model.get('maxInlines')).toBe(5);
            expect(model.get('minInlines')).toBe(1);

            expect(model.inlines.length).toBe(2);
            expect(view._inlineViews.length).toBe(2);

            let inline = model.inlines.at(0);
            expect(inline.get('index')).toBe(0);
            expect(inline.get('isInitial')).toBeTrue();
            expect(view._inlineViews[0].model).toBe(inline);

            inline = model.inlines.at(1);
            expect(inline.get('index')).toBe(1);
            expect(inline.get('isInitial')).toBeTrue();
            expect(view._inlineViews[1].model).toBe(inline);
        });

        it('Updated when inlines added', function() {
            buildView({
                numInlines: 1,
                initialForms: 1,
                totalForms: 1,
            });

            const $totalForms = $el.find('#id_myprefix-TOTAL_FORMS');
            const $addButton =
                $el.find('.rb-c-admin-form-inline-group__add-action');

            expect($el.find('.rb-c-admin-form-inline').length).toBe(1);
            expect($totalForms.val()).toBe('1');

            $addButton.click();
            expect($el.find('.rb-c-admin-form-inline').length).toBe(2);
            expect($totalForms.val()).toBe('2');

            $addButton.click();
            expect($el.find('.rb-c-admin-form-inline').length).toBe(3);
            expect($totalForms.val()).toBe('3');
        });

        it('Updated when inlines added', function() {
            buildView({
                numInlines: 2,
                initialForms: 2,
                totalForms: 2,
            });

            const $totalForms = $el.find('#id_myprefix-TOTAL_FORMS');

            expect(model.inlines.length).toBe(2);
            expect($totalForms.val()).toBe('2');

            model.inlines.at(0).destroy();

            const $inlines = $el.find('.rb-c-admin-form-inline');
            expect($inlines.length).toBe(1);
            expect(model.inlines.length).toBe(1);
            expect($totalForms.val()).toBe('1');
            expect($inlines[0].id).toBe('myprefix-0');
        });
    });

    describe('UI', function() {
        describe('Add Button', function() {
            let $addButton;

            beforeEach(function() {
                buildView({
                    numInlines: 1,
                    initialForms: 1,
                    minNumForms: 0,
                    maxNumForms: 3,
                    totalForms: 1,
                });

                $addButton =
                    $el.find('.rb-c-admin-form-inline-group__add-action');
                expect($addButton.length).toBe(1);
            });

            it('When under limit', function() {
                expect($addButton.is(':visible')).toBeTrue();

                view.addInlineForm();
                expect($addButton.is(':visible')).toBeTrue();
            });

            it('When limit hit', function() {
                expect($addButton.is(':visible')).toBeTrue();

                view.addInlineForm();
                view.addInlineForm();
                expect($addButton.is(':visible')).toBeFalse();
            });
        });
    });
});
