/*
 * Base class for hooks that an extension can use to augment functionality.
 *
 * Each type of hook represents a point in the codebase that an extension
 * is able to plug functionality into.
 *
 * Subclasses are expected to set a hookPoint field in the prototype to an
 * instance of ExtensionPoint.
 *
 * Instances of an ExtensionHook subclass that extensions create will be
 * automatically registered with both the extension and the list of hooks
 * for that ExtensionHook subclass.
 *
 * Callers that use ExtensionHook subclasses to provide functionality can
 * use the subclass's each() method to loop over all registered hooks.
 */
Djblets.ExtensionHook = Backbone.Model.extend({
    /*
     * An ExtensionHookPoint instance.
     *
     * This must be defined and instantiated by a subclass of ExtensionHook,
     * but not by subclasses created by extensions.
     */
    hookPoint: null,

    defaults: {
        extension: null
    },

    /*
     * Initializes the hook.
     *
     * This will add the instance of the hook to the extension's list of
     * hooks, and to the list of known hook instances for this hook point.
     *
     * After initialization, setUpHook will be called, which a subclass
     * can use to provide additional setup.
     */
    initialize: function() {
        var extension = this.get('extension');

        console.assert(this.hookPoint,
                       'This ExtensionHook subclass must define hookPoint');
        console.assert(extension,
                       'An Extension instance must be passed to ExtensionHook');

        extension.hooks.push(this);
        this.hookPoint.addHook(this);

        this.setUpHook();
    },

    /*
     * Sets up additional state for the hook.
     *
     * This can be overridden by subclasses to provide additional
     * functionality.
     */
    setUpHook: function() {
    }
}, {
    /*
     * Loops through each registered hook instance and calls the given
     * callback.
     */
    each: function(cb, context) {
        _.each(this.prototype.hookPoint.hooks, cb, context);
    }
});
