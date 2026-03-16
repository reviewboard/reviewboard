export {
    ResourceListItem as ConfigFormsResourceListItem,
} from './models/resourceListItemModel';


/*
 * We also define a legacy namespace for RB.Config.
 *
 * This doesn't play nicely with TypeScript-based code, so the above names are
 * preferable. The RB.Config.* names should be considered deprecated and
 * may be removed in a future release.
 */

import { ResourceListItem } from './models/resourceListItemModel';

export const Config = {
    ResourceListItem,
};
