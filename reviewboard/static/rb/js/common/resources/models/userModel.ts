/**
 * A model for a user.
 *
 * We don't currently have a resource implementation for the user API, but some
 * parts of the codebase use the resource data.
 *
 * Version Added:
 *     8.0
 */

import {
    type BaseResourceResourceData,
} from './baseResourceModel';


/**
 * Resource data for the user model.
 *
 * Version Added:
 *     8.0
 */
export interface UserResourceData extends BaseResourceResourceData {
    email: string;
    first_name: string;
    fullname: string;
    is_active: boolean;
    last_name: string;
    url: string;
    username: string;
}
