/*
 * A mixin for views that provides key binding functionality.
 *
 * Views using this mixin can provide a keyBindings map that maps a set of
 * key characters to a function.
 */
RB.KeyBindingsMixin = {
    /*
     * Enables key bindings for the view.
     *
     * Begins listening for any key bindings registered in the view's
     * keyBindings map, and calls the appropriate function.
     *
     * By default, this is called automatically when setting up the view,
     * by way of delegateEvents.
     */
    delegateKeyBindings: function() {
        this.$el.on('keypress.keybindings' + this.cid, _.bind(function(evt) {
            var keyChar,
                keys,
                func;

            if (evt.altKey || evt.ctrlKey || evt.metaKey ||
                evt.target.tagName === 'INPUT' ||
                evt.target.tagName === 'TEXTAREA' ||
                evt.target.isContentEditable) {
                /* These are all unsupported, and things we want to ignore. */
                return;
            }

            keyChar = String.fromCharCode(evt.which);

            for (keys in this.keyBindings) {
                if (_.has(this.keyBindings, keys)
                    && keys.indexOf(keyChar) !== -1) {

                    evt.stopPropagation();
                    evt.preventDefault();

                    func = this.keyBindings[keys];

                    if (!_.isFunction(func)) {
                        func = this[func];
                    }

                    func.call(this, evt);
                    return;
                }
            }
        }, this));
    },

    /*
     * Disables key bindings for the view.
     *
     * By default, this is called automatically when calling undelegateEvents.
     */
    undelegateKeyBindings: function() {
        this.$el.off('keypress.keybindings' + this.cid);
    },

    /*
     * Delegates both DOM events and key binding events.
     *
     * This overrides the default Backbone.View.delegateEvents to automatically
     * call delegateKeyBindings.
     */
    delegateEvents: function(events) {
        var result = Backbone.View.prototype.delegateEvents.call(this, events);

        this.delegateKeyBindings();

        return result;
    },

    /*
     * Undelegates both DOM events and key binding events.
     *
     * This overrides the default Backbone.View.undelegateEvents to
     * automatically call undelegateKeyBindings.
     */
    undelegateEvents: function() {
        var result = Backbone.View.prototype.undelegateEvents.call(this);

        this.undelegateKeyBindings();

        return result;
    }
};
