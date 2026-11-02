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
    type RepositoryFormAttrs,
    type RepositoryFormHostingAccount,
    type RepositoryFormHostingServiceInfo,
    type RepositoryFormPlan,
    type RepositoryFormSCMToolInfo,
    RepositoryForm,
} from './models/repositoryFormModel';

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
export {
    GitHubRepositoryFormView,
} from './views/gitHubRepositoryFormView';
export { LicenseView } from './views/licenseView';
export {
    type BugTrackerConfigInfo,
    type RepositoryBugTrackersViewOptions,
    type ServiceBugTrackerInfo,
    RepositoryBugTrackersView,
} from './views/repositoryBugTrackersView';
export {
    type RepositoryFormViewOptions,
    RepositoryFormView,
} from './views/repositoryFormView';
export {
    type HostingServiceRepositoryFormViewOptions,
    HostingServiceRepositoryFormView,
} from './views/hostingServiceRepositoryFormView';
export {
    SCMToolRepositoryFormView,
} from './views/scmToolRepositoryFormView';


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
import { RepositoryForm } from './models/repositoryFormModel';
import {
    RepositoryBugTrackersView,
} from './views/repositoryBugTrackersView';
import { RepositoryFormView } from './views/repositoryFormView';
import {
    GitHubRepositoryFormView,
} from './views/gitHubRepositoryFormView';
import {
    HostingServiceRepositoryFormView,
} from './views/hostingServiceRepositoryFormView';
import {
    SCMToolRepositoryFormView,
} from './views/scmToolRepositoryFormView';

export const Admin = {
    BugTrackerFormView,
    ConnectServiceWizardView,
    ConnectedServicesView,
    GitHubRepositoryFormView,
    HostingServiceRepositoryFormView,
    PageView: BaseAdminPageView,
    RepositoryBugTrackersView,
    RepositoryForm,
    RepositoryFormView,
    SCMToolRepositoryFormView,
    connectedServiceMenuActions,
};
