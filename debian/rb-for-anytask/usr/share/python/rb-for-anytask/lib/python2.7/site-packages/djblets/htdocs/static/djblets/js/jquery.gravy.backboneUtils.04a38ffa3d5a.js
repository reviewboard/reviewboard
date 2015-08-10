/*
 * Binds setting a CSS class on an element to a model's property.
 *
 * The CSS class will be added when the property is true (or false, if
 * options.inverse is set). Otherwise, it will be removed from the element.
 */
$.fn.bindClass = function(model, modelPropName, className, options) {
    function updateClassName() {
        var value = model.get(modelPropName);

        if (options && options.inverse) {
            value = !value;
        }

        if (value) {
            this.addClass(className);
        } else {
            this.removeClass(className);
        }
    }

    model.on('change:' + modelPropName, updateClassName, this);
    updateClassName.call(this);

    return this;
};


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
 * There are special property names that bindProperty understands, which will
 * update the state of an element but not through a $.prop call. These are
 * 'text' (using $el.text()) and 'html' ($el.html()).
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
 *
 * If options.radioValue is set, then the assumption is that a boolean
 * property on the element (such as 'checked') maps to a non-boolean value
 * in a model, of which many inputs will be bound. In this case, the element's
 * property will be set to a boolean based on whether the model property's
 * value matches option.radioValue. Likewise, the model property's value will
 * be set to options.radioValue if the element's property value is true.
 */
$.fn.bindProperty = function(elPropName, model, modelPropName, options) {
    function updateElementProp() {
        var value = model.get(modelPropName);

        if (options.radioValue !== undefined) {
            value = (options.radioValue === value);
        }

        if (options.inverse) {
            value = !value;
        }

        if (elPropName === 'text' || elPropName === 'html') {
            if ($this[elPropName]() !== value) {
                $this[elPropName]((value === undefined ||
                                   value === null)
                                  ? '' : value);
            }
        } else if ($this.prop(elPropName) !== value) {
            $this.prop(elPropName, value);
        }
    }

    var $this = this;

    options = _.defaults(options || {}, {
        modelToElement: true,
        elementToModel: true,
        inverse: false,
        radioValue: undefined
    });

    if (options.modelToElement) {
        model.on('change:' + modelPropName, updateElementProp);
        updateElementProp();
    }

    if (options.elementToModel) {
        $this.on('change', function() {
            var value = (elPropName === 'text' || elPropName === 'html')
                        ? $this[elPropName]()
                        : $this.prop(elPropName);

            if (options.inverse) {
                value = !value;
            }

            if (options.radioValue !== undefined) {
                if (value) {
                    value = options.radioValue;
                } else {
                    return;
                }
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
    function updateVisibility() {
        var value = model.get(modelPropName);

        if (options && options.inverse) {
            value = !value;
        }

        this.setVisible(value);
    }

    model.on('change:' + modelPropName, updateVisibility, this);
    updateVisibility.call(this);

    return this;
};
