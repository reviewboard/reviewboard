/**
 * A model for holding a resource's extra data.
 */

import { BaseModel, spina } from '@beanbag/spina';


/**
 * A model for holding a resource's extra data.
 *
 * Contains utility methods for serializing it.
 */
@spina
export class ExtraData extends BaseModel {
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
    toJSON(): object {
        const data = {};

        for (const [key, value] of Object.entries(this.attributes)) {
            data[`extra_data.${key}`] = value;
        }

        return data;
    }
}
