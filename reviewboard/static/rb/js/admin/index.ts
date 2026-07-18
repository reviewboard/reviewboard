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

export {
    type AccountMenuActionContext,
    type AccountMenuActionHandler,
    type AccountMenuItem,
    connectedServiceMenuActions,
} from './connectedServiceMenuActions';
export { BaseAdminPageView } from './views/baseAdminPageView';
export { BugTrackerFormView } from './views/bugTrackerFormView';
export {
    type ConnectServiceInfo,
    type ConnectServiceWizardViewOptions,
    ConnectServiceWizardView,
} from './views/connectServiceWizardView';
export {
    type ConnectedServicesViewOptions,
    ConnectedServicesView,
} from './views/connectedServicesView';
export { LicenseView } from './views/licenseView';


/* Legacy namespace for RB.Admin. */
import { connectedServiceMenuActions } from './connectedServiceMenuActions';
import { BaseAdminPageView } from './views/baseAdminPageView';
import { BugTrackerFormView } from './views/bugTrackerFormView';
import {
    ConnectServiceWizardView,
} from './views/connectServiceWizardView';
import {
    ConnectedServicesView,
} from './views/connectedServicesView';

export const Admin = {
    BugTrackerFormView,
    ConnectServiceWizardView,
    ConnectedServicesView,
    PageView: BaseAdminPageView,
    connectedServiceMenuActions,
};
