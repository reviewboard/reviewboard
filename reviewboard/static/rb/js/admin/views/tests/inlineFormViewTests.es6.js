suite('rb/admin/views/InlineFormView', function() {
    const template = _.template(dedent`
        <div class="rb-c-admin-form-inline">
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
           <label for="id_myprefix-<%- index %>-foo"></label>
           <input id="id_myprefix-<%- index %>-foo"
                  name="myprefix-<%- index %>-foo">
          </div>
          <div>
           <label for="id_myprefix-<%- index %>-bar"></label>
           <input id="id_myprefix-<%- index %>-bar"
                  name="myprefix-<%- index %>-bar">
          </div>
         </fieldset>
        </div>
    `);

    let $el;
    let model;
    let view;

    beforeEach(function() {
        $el = $(template({
            index: '__prefix__',
        }));

        model = new RB.Admin.InlineForm({
            prefix: 'myprefix',
        });

        view = new RB.Admin.InlineFormView({
            el: $el,
            model: model,
        });
        view.render();
    });

    describe('Events', function() {
        describe('Delete clicked', function() {
            let $delete;

            beforeEach(function() {
                spyOn(window, 'confirm').and.returnValue(true);
                spyOn(model, 'destroy');

                $delete = $el.find('.rb-c-admin-form-inline__delete-action');
            });

            it('With isInitial=true', function() {
                model.set('isInitial', true);

                $delete.click();

                expect(window.confirm).not.toHaveBeenCalled();
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With isInitial=false', function() {
                model.set('isInitial', false);

                $delete.click();

                expect(window.confirm).toHaveBeenCalled();
                expect(model.destroy).toHaveBeenCalled();
            });
        });

        describe('Index changed', function() {
            let $labels;
            let $inputs;
            let $titleIndex;

            beforeEach(function() {
                $labels = $el.find('label');
                $inputs = $el.find('input');
                $titleIndex = $el.find('.rb-c-admin-form-inline__title-index');

                expect($labels.length).toBe(2);
                expect($inputs.length).toBe(2);
                expect($titleIndex.length).toBe(1);
            });

            it('From __prefix__ to index', function() {
                model.set('index', 0);

                expect($el[0].id).toBe('myprefix-0');
                expect($titleIndex.text()).toBe('#1');

                expect($labels[0].htmlFor).toBe('id_myprefix-0-foo');
                expect($labels[1].htmlFor).toBe('id_myprefix-0-bar');

                let inputEl = $inputs[0];
                expect(inputEl.id).toBe('id_myprefix-0-foo');
                expect(inputEl.name).toBe('myprefix-0-foo');

                inputEl = $inputs[1];
                expect(inputEl.id).toBe('id_myprefix-0-bar');
                expect(inputEl.name).toBe('myprefix-0-bar');
            });

            it('From index to index', function() {
                model.set('index', 0);
                model.set('index', 1);

                expect($el[0].id).toBe('myprefix-1');
                expect($titleIndex.text()).toBe('#2');

                expect($labels[0].htmlFor).toBe('id_myprefix-1-foo');
                expect($labels[1].htmlFor).toBe('id_myprefix-1-bar');

                let inputEl = $inputs[0];
                expect(inputEl.id).toBe('id_myprefix-1-foo');
                expect(inputEl.name).toBe('myprefix-1-foo');

                inputEl = $inputs[1];
                expect(inputEl.id).toBe('id_myprefix-1-bar');
                expect(inputEl.name).toBe('myprefix-1-bar');
            });
        });
    });
});
