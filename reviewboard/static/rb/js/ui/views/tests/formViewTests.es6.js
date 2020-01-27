suite('rb/ui/views/FormView', function() {
    const template = dedent`
        <form class="rb-c-form">
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
        </form>
    `;

    let view;

    beforeEach(function() {
        view = new RB.FormView({
            el: $(template),
        });
        view.render();
    });

    describe('Fieldsets', function() {
        it('Collapsing', function() {
            const $fieldset = view.$('.rb-c-form-fieldset:nth-child(1)');

            expect($fieldset.hasClass('-is-collapsed')).toBe(false);

            $fieldset.find('.rb-c-form-fieldset__toggle').click();

            expect($fieldset.hasClass('-is-collapsed')).toBe(true);
            expect($fieldset.find('.rb-c-form-fieldset__toggle').text())
                .toBe('(Show)');
        });

        it('Expanding', function() {
            const $fieldset = view.$('.rb-c-form-fieldset:nth-child(2)');

            expect($fieldset.hasClass('-is-collapsed')).toBe(true);

            $fieldset.find('.rb-c-form-fieldset__toggle').click();

            expect($fieldset.hasClass('-is-collapsed')).toBe(false);
            expect($fieldset.find('.rb-c-form-fieldset__toggle').text())
                .toBe('(Hide)');
        });
    });
});
