/*
 * Defines a point where extension hooks can plug into.
 *
 * This is meant to be instantiated and provided as a 'hookPoint' field on
 * an ExtensionHook subclass, in order to provide a place to hook into.
 */
Djblets.ExtensionHookPoint = Backbone.Model.extend({
    initialize: function() {
        this.hooks = [];
    },

    /*
     * Adds a hook instance to the list of known hooks.
     */
    addHook: function(hook) {
        this.hooks.push(hook);
    }
});
