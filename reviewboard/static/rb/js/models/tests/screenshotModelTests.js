describe('models/Screenshot', function() {
    var parentObject,
        model;

    beforeEach(function(){
        parentObject = new RB.BaseResource({
            public: true
        });

        model = new RB.Screenshot({
            parentObject: parentObject
        });
    });

    describe('toJSON', function() {
        describe('caption field', function() {
            it('With value', function() {
                var data;

                model.set('caption', 'foo');
                data = model.toJSON();
                expect(data.caption).toBe('foo');
            });
        });
    });
});
