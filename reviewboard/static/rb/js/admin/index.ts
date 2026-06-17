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
export {
    type ConnectServiceInfo,
    type ConnectServiceWizardViewOptions,
    ConnectServiceWizardView,
} from './views/connectServiceWizardView';
export { LicenseView } from './views/licenseView';


/* Legacy namespace for RB.Admin. */
import { BaseAdminPageView } from './views/baseAdminPageView';
import {
    ConnectServiceWizardView,
} from './views/connectServiceWizardView';

export const Admin = {
    ConnectServiceWizardView,
    PageView: BaseAdminPageView,
};
