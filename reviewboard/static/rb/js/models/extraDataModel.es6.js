/**
 * A model for holding a resource's extra data.
 *
 * Contains utility methods for serializing it.
 */
RB.ExtraData = Backbone.Model.extend({
    /**
     * JSONify the extra data.
     *
     * The extra data is serialized such that each key is prefixed with
     * "extra_data." so that the API can understand it. The result of this
     * function should be merged into the serialization of the parent object.
     *
     * Returns:
     *     object:
     *     An object suitable for serializing to JSON.
     */
    toJSON() {
        const data = {};

        _.each(this.attributes, (value, key) => {
            data[`extra_data.${key}`] = value;
        });

        return data;
    },
});
