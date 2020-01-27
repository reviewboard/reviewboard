suite('rb/admin/models/InlineFormGroup', function() {
    let model;

    beforeEach(function() {
        model = new RB.Admin.InlineFormGroup();
    });

    describe('Methods', function() {
        describe('canAddInline', function() {
            it('With no limit', function() {
                model.set('maxInlines', null);

                expect(model.canAddInline()).toBeTrue();
            });

            it('With limit not reached', function() {
                model.set('maxInlines', 2);
                model.inlines.add({});

                expect(model.canAddInline()).toBeTrue();
            });

            it('With limit reached', function() {
                model.set('maxInlines', 2);
                model.inlines.add([{}, {}]);

                expect(model.canAddInline()).toBeFalse();
            });
        });
    });
});
