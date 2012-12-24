/*
 * Binds properties on an element and a model together.
 *
 * This can be used to ensure that a model and an element have properties in
 * sync. For example, a checkbox's "checked" property, or a "disabled" property,
 * backed by state in a model.
 *
 * By default, the element's property will be set to the model's current
 * property, and future changes to either will update the other.
 *
 * If options.modelToElement is false, then the element will not be updated
 * when the model's state changes, or updated to the initial model's state.
 *
 * If options.elementToModel is false, then the model will not be updated
 * when the element's state changes.
 *
 * If options.inverse is true, then the value will be inversed between both
 * properties. This is useful when tying a "disabled" element property to
 * an "enabled" or "can*" model property. It only makes sense for boolean
 * properties.
 */
$.fn.bindProperty = function(elPropName, model, modelPropName, options) {
    var $this = $(this);

    options = _.defaults(options || {}, {
        modelToElement: true,
        elementToModel: true,
        inverse: false
    });

    if (options.modelToElement) {
        function updateElementProp() {
            var value = model.get(modelPropName);

            if (options.inverse) {
                value = !value;
            }

            if ($this.prop(elPropName) !== value) {
                $this.prop(elPropName, value);
            }
        };

        model.on('change:' + modelPropName, updateElementProp);
        updateElementProp();
    }

    if (options.elementToModel) {
        $this.on('change', function(value) {
            var value = $this.prop(elPropName);

            if (options.inverse) {
                value = !value;
            }

            model.set(modelPropName, value);
        });
    }

    return $this;
};


/*
 * Binds the visibility of an element to a model's property.
 *
 * The element's initial visibility will be set to the boolean property
 * value on the model. When the property on the model changes, the
 * visibility will update to reflect that.
 *
 * If options.inverse is true, then the value will be inversed between both
 * properties. This is used when trying a hide an element when a property
 * in a model is "true", or show an element when the value is "false".
 */
$.fn.bindVisibility = function(model, modelPropName, options) {
    var $this = $(this);

    function updateVisibility() {
        var value = model.get(modelPropName);

        if (options && options.inverse) {
            value = !value;
        }

        $this.setVisible(value);
    }

    model.on('change:' + modelPropName, updateVisibility);
    updateVisibility();

    return $this;
};
