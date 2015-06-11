suite('rb/models/ExtraData', function() {
    var resource,
        model;

    beforeEach(function() {
        resource = Backbone.Model.extend(_.defaults({
            defaults: function() {
                return {
                    extraData: new RB.ExtraData()
                };
            },

            initialize: function() {
                this.listenTo(this.get('extraData'), 'change',
                              this._onExtraDataChanged)
            }
        }, RB.ExtraDataMixin));

        model = new resource();
    });

    it('change events fired', function() {
        var callbacks = {
            'change': function() {},
            'change:extraData': function() {}
        };

        spyOn(callbacks, 'change');
        spyOn(callbacks, 'change:extraData');

        model.on('change', callbacks.change);
        model.on('change:extraData', callbacks['change:extraData']);

        model.get('extraData').set('foo', 1);

        expect(callbacks.change).toHaveBeenCalled();
        expect(callbacks['change:extraData']).toHaveBeenCalled();
    });
});
