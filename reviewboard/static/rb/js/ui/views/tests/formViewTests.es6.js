suite('rb/ui/views/FormView', function() {
    const template = dedent`
        <form class="rb-c-form">
         <select id="subform1-selector"
                 data-subform-group="group1">
          <option value="subform1">subform1</option>
          <option value="subform2">subform2</option>
         </select>

         <fieldset class="rb-c-form-fieldset">
          <legend class="rb-c-form-fieldset__name">
           Title
           <a href="#" class="rb-c-form-fieldset__toggle">(Hide)</a>
          </legend>
          <div class="rb-c-form-fieldset__content"></div>
         </fieldset>
         <fieldset class="rb-c-form-fieldset -is-collapsed">
          <legend class="rb-c-form-fieldset__name">
           Title
           <a href="#" class="rb-c-form-fieldset__toggle">(Show)</a>
          </legend>
          <div class="rb-c-form-fieldset__content"></div>
         </fieldset>

         <fieldset class="rb-c-form-fieldset -is-subform"
                   data-subform-controller="subform1-selector"
                   data-subform-id="subform1">
         </fieldset>
         <fieldset class="rb-c-form-fieldset -is-subform"
                   data-subform-controller="subform1-selector"
                   data-subform-id="subform2">
         </fieldset>

         <fieldset class="rb-c-form-fieldset -is-subform"
                   data-subform-group="group2"
                   data-subform-id="subform3">
         </fieldset>
         <fieldset class="rb-c-form-fieldset -is-subform"
                   data-subform-group="group2"
                   data-subform-id="subform4"
                   disabled hidden>
         </fieldset>
        </form>
    `;

    let view;
    let $subforms;

    beforeEach(function() {
        view = new RB.FormView({
            el: $(template),
        });
        view.render().$el.appendTo($testsScratch);

        $subforms = view._$subforms;
    });

    function checkSubformVisibility(index, visible) {
        const $subform = $subforms.eq(index);

        expect($subform.prop('disabled')).toBe(!visible);
        expect($subform.prop('hidden')).toBe(!visible);
    }

    describe('Fieldsets', function() {
        it('Collapsing', function() {
            const $fieldset = view.$('.rb-c-form-fieldset').eq(0);

            expect($fieldset.hasClass('-is-collapsed')).toBe(false);

            $fieldset.find('.rb-c-form-fieldset__toggle').click();

            expect($fieldset.hasClass('-is-collapsed')).toBe(true);
            expect($fieldset.find('.rb-c-form-fieldset__toggle').text())
                .toBe('(Show)');
        });

        it('Expanding', function() {
            const $fieldset = view.$('.rb-c-form-fieldset').eq(1);

            expect($fieldset.hasClass('-is-collapsed')).toBe(true);

            $fieldset.find('.rb-c-form-fieldset__toggle').click();

            expect($fieldset.hasClass('-is-collapsed')).toBe(false);
            expect($fieldset.find('.rb-c-form-fieldset__toggle').text())
                .toBe('(Hide)');
        });
    });

    describe('Subforms', function() {
        it('Loaded state', function() {
            expect($subforms.length).toBe(4);
            expect(_.keys(view._subformsByGroup))
                .toEqual(['group1', 'group2']);
            expect(_.keys(view._subformsByGroup.group1))
                .toEqual(['subform1', 'subform2']);
            expect(_.keys(view._subformsByGroup.group2))
                .toEqual(['subform3', 'subform4']);
            expect(view._subformsByGroup.group1.subform1[0])
                .toBe($subforms[0]);
            expect(view._subformsByGroup.group1.subform2[0])
                .toBe($subforms[1]);
            expect(view._subformsByGroup.group2.subform3[0])
                .toBe($subforms[2]);
            expect(view._subformsByGroup.group2.subform4[0])
                .toBe($subforms[3]);

            checkSubformVisibility(0, true);
            checkSubformVisibility(1, false);
            checkSubformVisibility(2, true);
            checkSubformVisibility(3, false);
        });

        it('Controller value changed', function() {
            view.$el.children('select')
                .val('subform2')
                .triggerHandler('change');

            checkSubformVisibility(0, false);
            checkSubformVisibility(1, true);
            checkSubformVisibility(2, true);
            checkSubformVisibility(3, false);
        });
    });

    describe('Methods', function() {
        describe('setSubformVisibility', function() {
            it('With group', function() {
                view.setSubformVisibility({
                    group: 'group2',
                });

                checkSubformVisibility(2, false);
                checkSubformVisibility(3, false);
            });

            it('With group, visible', function() {
                view.setSubformVisibility({
                    group: 'group2',
                    visible: true,
                });

                checkSubformVisibility(2, true);
                checkSubformVisibility(3, true);

                view.setSubformVisibility({
                    group: 'group2',
                    visible: false,
                });

                checkSubformVisibility(2, false);
                checkSubformVisibility(3, false);
            });

            it('With group, subformID, visible', function() {
                checkSubformVisibility(2, true);

                view.setSubformVisibility({
                    group: 'group2',
                    subformID: 'subform3',
                    visible: false,
                });

                checkSubformVisibility(2, false);
                checkSubformVisibility(3, false);

                view.setSubformVisibility({
                    group: 'group2',
                    subformID: 'subform4',
                    visible: true,
                });

                checkSubformVisibility(3, true);
            });

            it('With group, subformID, visible, hideOthers', function() {
                view.setSubformVisibility({
                    group: 'group1',
                    subformID: 'subform2',
                    visible: true,
                    hideOthers: true,
                });

                checkSubformVisibility(0, false);
                checkSubformVisibility(1, true);

                view.setSubformVisibility({
                    group: 'group1',
                    subformID: 'subform1',
                    visible: true,
                    hideOthers: true,
                });

                checkSubformVisibility(0, true);
                checkSubformVisibility(1, false);
            });
        });
    });
});
