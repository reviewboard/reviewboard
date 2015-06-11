RB.ExtraDataMixin = {
    /*
     * Set the key to the value with the give options.
     *
     * This is a special case of Backbone.Model's set which does some extra
     * work when dealing with a extraData member. It ensures that extraData is
     * only ever set to an instance of RB.ExtraData and sets up a listener
     * to fire change events when the extraData fires a change event.
     */
    set: function(key, value, options) {
        var attrs,
            extraData,
            newExtraData;

        if (_.isObject(key)) {
            attrs = key;
            options = value;
        } else {
            attrs = {};
            attrs[key] = value;
        }

        if (_.has(attrs, 'extraData') && _.has(this.attributes, 'extraData')) {
            extraData = this.get('extraData');

            newExtraData = attrs.extraData;
            delete attrs.extraData;

            if (newExtraData instanceof RB.ExtraData) {
                newExtraData = _.clone(newExtraData.attributes);
            }

            extraData.clear();
            extraData.set(newExtraData, options);
        }

        return Backbone.Model.prototype.set.call(this, attrs, options);
    },

    /*
     * Handle a change event fired from the model's extra data.
     *
     * This fires both the change and change:extraData for this model.
     */
    _onExtraDataChanged: function(extraData, options) {
        this.trigger('change', this, options);
        this.trigger('change:extraData', this, extraData, options);
    },

    /*
     * Get the key from the model's extra data.
     *
     * This should only be used when the model has an extraData attribute.
     */
    getExtraData: function(key) {
        return this.get('extraData').get(key);
    },

    /*
     * Set the key in the model's extra data to the value.
     *
     * This should only be used when the model has an extraData attribute.
     */
    setExtraData: function(key, value) {
        this.get('extraData').set(key, value);
    }
};
