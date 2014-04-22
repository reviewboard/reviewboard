suite('rb/resources/models/Screenshot', function() {
    var parentObject,
        model;

    beforeEach(function(){
        parentObject = new RB.BaseResource({
            'public': true
        });

        model = new RB.Screenshot({
            parentObject: parentObject
        });
    });

    describe('getDisplayName', function() {
        it('With caption', function() {
            model.set('caption', 'My Caption');

            expect(model.getDisplayName()).toBe('My Caption');
        });

        it('With filename', function() {
            model.set('filename', 'myfile.png');

            expect(model.getDisplayName()).toBe('myfile.png');
        });

        it('With caption and filename', function() {
            model.set({
                caption: 'My Caption',
                filename: 'myfile.png'
            });

            expect(model.getDisplayName()).toBe('My Caption');
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                screenshot: {
                    id: 42,
                    caption: 'my-caption',
                    filename: 'my-filename',
                    review_url: '/review-ui/'
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.caption).toBe('my-caption');
            expect(data.filename).toBe('my-filename');
            expect(data.reviewURL).toBe('/review-ui/');
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
