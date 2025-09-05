export {
    LicenseCollection,
} from './collections/licenseCollection';

export {
    type LicenseAttrs,
    License,
    LicenseCheckStatus,
    LicenseStatus,
} from './models/licenseModel';
export { CallLicenseActionError } from './models/callLicenseActionError';

export { BaseAdminPageView } from './views/baseAdminPageView';
export { LicenseView } from './views/licenseView';


/* Legacy namespace for RB.Admin. */
import { BaseAdminPageView } from './views/baseAdminPageView';

export const Admin = {
    PageView: BaseAdminPageView,
};
