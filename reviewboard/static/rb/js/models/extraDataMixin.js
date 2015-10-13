/*
 * A mixin to add a new extra data API to a model.
 *
 * The model this is attached to gains an extraData property that is backed by
 * the extraData key of the model's attributes object. This new API also
 * enhances the model such that extraData object can be interacted with on in a
 * key-value manner instead of dealing with the whole object.
 *
 * Any class that inherits this mixin should call _setupExtraData in its
 * initialize function to ensure that the mixin will work properly. This will
 * set up the property and event listeners.
 */
RB.ExtraDataMixin = {
    /*
     * Set up the resource to add the new extra data API.
     *
     * This function should be called in the model's initialize function.
     *
     * This adds an extraData attribute that is backed by the model's
     * attribute.extraData. This new model.extraData can be used directly in a
     * model.extraData.get/set fashion to get or set individual keys in the
     * extra data, instead of getting and setting the extra data all at once.
     *
     * This will also set up event listeners so that changes to extraData
     * through the RB.ExtraData instance will trigger changed events on the
     * model itself
     */
    _setupExtraData: function() {
        this.extraData = new RB.ExtraData();
        this.extraData.attributes = this.attributes.extraData;

        this.listenTo(this.extraData, 'change', this._onExtraDataChanged);
    },

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
            useExtraData;

        if (_.isObject(key)) {
            attrs = key;
            options = value;
        } else {
            attrs = {};
            attrs[key] = value;
        }

        useExtraData = _.has(attrs, 'extraData') && _.has(this, 'extraData');

        if (useExtraData) {
            if (attrs.extraData instanceof RB.ExtraData) {
                /*
                 * We don't want to assign an RB.ExtraData instance to the
                 * model's extraData attribute because it expects a plain
                 * JavaScript object.
                 */
                attrs.extraData = _.clone(attrs.extraData.attributes);
            }
        }

        Backbone.Model.prototype.set.call(this, attrs, options);

        if (useExtraData) {
            this.extraData.attributes = this.attributes.extraData;
        }

        return this;
    },

    /*
     * Handle a change event fired from the model's extra data.
     *
     * This fires both the change and change:extraData for this model.
     */
    _onExtraDataChanged: function(extraData, options) {
        this.trigger('change:extraData', this, extraData, options);
        this.trigger('change', this, options);
    },

    /*
     * Get the key from the model's extra data.
     *
     * This should only be used when the model has an extraData attribute.
     */
    getExtraData: function(key) {
        return this.extraData.get(key);
    },

    /*
     * Set the key in the model's extra data to the value.
     *
     * This should only be used when the model has an extraData attribute.
     */
    setExtraData: function(key, value) {
        this.extraData.set(key, value);
    }
};
