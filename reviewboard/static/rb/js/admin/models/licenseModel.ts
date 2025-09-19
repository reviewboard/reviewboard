/**
 * Models for managing Review Board licensing.
 *
 * This module provides models and types for handling Review Board's licensing
 * system, including license status tracking, updates, and management.
 *
 * Version Added:
 *     7.1
 */

import {
    BaseModel,
    spina,
} from '@beanbag/spina';

import {
    CallLicenseActionError,
} from './callLicenseActionError';

import {
    type LicenseCollection,
} from '../collections/licenseCollection';


/**
 * The current status of a license.
 *
 * Version Added:
 *     7.1
 */
export enum LicenseStatus {
    /** No license is currently active. */
    UNLICENSED = 'unlicensed',

    /** A valid license is active. */
    LICENSED = 'licensed',

    /** The license has expired but is in a grace period. */
    EXPIRED_GRACE_PERIOD = 'expired-grace-period',

    /** The license has expired with no grace period remaining. */
    HARD_EXPIRED = 'hard-expired',
}


/**
 * The status of a license check operation.
 *
 * Version Added:
 *     7.1
 */
export enum LicenseCheckStatus {
    /** Checking for an updated license. */
    CHECKING = 'checking',

    /** The latest license has already been applied. */
    HAS_LATEST = 'has-latest',

    /** Applying a new license. */
    APPLYING = 'applying',

    /** A new license has been applied. */
    APPLIED = 'applied',

    /** There is no accessible license. */
    NO_LICENSE = 'no-license',

    /** There was an error checking for a new license. */
    ERROR_CHECKING = 'error-checking',

    /** There was an error applying a new license. */
    ERROR_APPLYING = 'error-applying',
}


/**
 * Response payload from checking for license updates.
 *
 * This is returned by Review Board.
 *
 * Version Added:
 *     7.1
 */
export interface CheckUpdatesProcessResponsePayload {
    /** The current status of the license check. */
    status: LicenseCheckStatus;

    /** Optional license information to set. */
    license_infos?: Record<string, Record<string, unknown>>;
}


/**
 * Options for calling an action on the license provider.
 *
 * Version Added:
 *     7.1
 */
export interface CallActionOptions {
    /** The name of the action. */
    action: string;

    /** Encoded arguments for the action. */
    args?: Record<string, unknown>;

    /** Uploaded content for the action. */
    uploads?: Record<string, Blob>;
}


/**
 * A displayed action that can be taken on a license.
 *
 * Version Added:
 *     7.1
 */
export interface LicenseAction {
    /** The unique identifier for this action. */
    actionID: string;

    /** The display label for this action. */
    label: string;

    /** Arguments to pass in a call. */
    callArgs?: Record<string, unknown>;

    /** Extra data provided for the client-side action handler. */
    extraData?: Record<string, unknown>;

    /** Whether this is a primary button. */
    primary?: boolean;

    /** The URL to perform this action. */
    url?: string;
}


/**
 * A displayed line item for the license.
 *
 * Version Added:
 *     7.1
 */
export interface LicenseLineItem {
    /**
     * The content for the line item.
     *
     * This may be a plain text string (which will be escaped) or a safe
     * HTML-formatted string, depending on the :js:attr:`contentIsHTML` flag.
     */
    content: string;

    /** Whether the content should be rendered as HTML. */
    contentIsHTML?: boolean;

    /** THe optional icon CSS class name to display alongside the content. */
    icon?: string;
}


/**
 * Attributes for a license.
 *
 * Version Added:
 *     7.1
 */
export interface LicenseAttrs {
    /** The target used for any actions invoked on behalf of the license. */
    actionTarget: string;

    /**
     * The license identifier.
     *
     * This is unique within the license provider.
     */
    licenseID: string;

    /** Available actions for this license. */
    actions?: LicenseAction[] | null;

    /** Whether this license supports manual upload of new license data. */
    canUploadLicense?: boolean;

    /** The current status for any license checks. */
    checkStatus?: LicenseCheckStatus;

    /** The date when the license expires or expired. */
    expiresDate?: Date | null;

    /** Whether the license is about to expire. */
    expiresSoon?: boolean;

    /** Number of days remaining in the grace period. */
    gracePeriodDaysRemaining?: number | null,

    /** The date when the license hard expires or expired. */
    hardExpiresDate?: Date | null,

    /** Whether this is a trial license. */
    isTrial?: boolean;

    /** The entity this license is assigned to. */
    licensedTo?: string | null;

    /** A list of line items to display in the license. */
    lineItems?: LicenseLineItem[] | null;

    /** The URL for managing the license on a license portal. */
    manageURL?: string | null;

    /** A notice to display below the summary. */
    noticeHTML?: string | null;

    /** The plan identifier. */
    planID?: string | null;

    /** The name of the plan. */
    planName?: string | null;

    /** The name of the product. */
    productName?: string | null;

    /** The current status of the license. */
    status?: LicenseStatus;

    /** A summary of the license. */
    summary?: string | null;

    /** Any warning associated with the license. */
    warningHTML?: string | null;
}


/**
 * Options for a license.
 *
 * Version Added:
 *     7.1
 */
export interface LicenseOptions {
    /** CSRF token for any actions performed on this license. */
    actionCSRFToken: string;
}


/**
 * Model for managing a Review Board license.
 *
 * This model handles license status tracking, updates, and management
 * operations.
 *
 * Version Added:
 *     7.1
 */
@spina({
    prototypeAttrs: ['actionBuilders'],
})
export class License<
    TAttrs extends LicenseAttrs = LicenseAttrs,
    TExtraOptions extends LicenseOptions = LicenseOptions,
    TOptions = Backbone.ModelSetOptions,
> extends BaseModel<TAttrs, TExtraOptions, TOptions> {
    static idAttribute = 'licenseID';

    static defaults: LicenseAttrs = {
        actionTarget: null,
        actions: null,
        canUploadLicense: false,
        checkStatus: LicenseCheckStatus.HAS_LATEST,
        expiresDate: null,
        expiresSoon: false,
        gracePeriodDaysRemaining: null,
        hardExpiresDate: null,
        isTrial: false,
        licenseID: null,
        licensedTo: null,
        lineItems: null,
        manageURL: null,
        noticeHTML: null,
        planID: null,
        planName: null,
        productName: null,
        status: LicenseStatus.UNLICENSED,
        summary: null,
        warningHTML: null,
    };

    /**********************
     * Instance variables *
     **********************/

    /** CSRF token for any actions performed on this license. */
    actionCSRFToken: string;

    /**
     * Initialize the license.
     *
     * Args:
     *     attrs (LicenseAttrs):
     *         The initial attributes for the license.
     *
     *     options (LicenseOptions):
     *         Options for the license.
     */
    initialize(
        attributes?: LicenseAttrs,
        options?: Backbone.CombinedModelConstructorOptions<
            TExtraOptions,
            this
        >,
    ) {
        this.actionCSRFToken = options?.actionCSRFToken;
    }

    /**
     * Upload a new set of license data to the license provider.
     *
     * Args:
     *     contents (Blob):
     *         The binary contents of the file to upload.
     *
     * Returns:
     *     Promise:
     *     The promise for the upload request.
     */
    async uploadLicenseFile(contents: Blob) {
        await this.callAction({
            action: 'upload-license',
            uploads: {
                license_data: contents,
            },
        });
    }

    /**
     * Call an action in the license provider backend.
     *
     * Args:
     *     options (CallActionOptions):
     *         Options for the action call.
     *
     * Returns:
     *     Promise:
     *     The promise for the action call.
     */
    async callAction(
        options: CallActionOptions,
    ): Promise<unknown> {
        /*
         * For this, we're going to use $.ajax instead of RB.apiCall, so
         * that we don't have to worry about turning things off like the
         * activity indicator or dealing with anything specific to the
         * Review Board API.
         *
         * Also, let any errors bubble up.
         */
        const action = options.action;
        const actionTarget = this.get('actionTarget');

        const formData = new FormData();
        formData.append('action', action);
        formData.append('action_target', actionTarget);
        formData.append('csrfmiddlewaretoken', this.actionCSRFToken);

        if (options.args) {
            formData.append('action_data', JSON.stringify(options.args));
        }

        if (options.uploads) {
            for (const [key, value] of Object.entries(options.uploads)) {
                formData.append(key, value);
            }
        }

        let response: Response = null;
        let rsp;

        try {
            response = await fetch('.', {
                body: formData,
                method: 'POST',
            });

            rsp = await response.json();
        } catch (err) {
            /* Fall through and handle this below. */
        }

        if (!rsp || !response.ok) {
            throw new CallLicenseActionError({
                action: action,
                actionTarget: actionTarget,
                message: rsp?.error,
                response: response,
            });
        }

        return rsp;
    }

    /**
     * Check for license updates.
     *
     * This will start by fetching request data from the license provider's
     * configured endpoint, passing in the data needed for the request. If
     * successful, the data will be processed by the license provider backend
     * in Review Board, returning new attributes .
     *
     * The status will be updated throughout the process to reflect the current
     * state. Listeners can monitor the ``checkStatus`` attribute for changes.
     * Upon completion, the ``licenseUpdates`` event will be triggered.
     */
    async checkForUpdates() {
        this.set('checkStatus', LicenseCheckStatus.CHECKING);

        /* Fetch a license check request payload. */
        let checkRsp;

        try {
            checkRsp = await this.callAction({
                action: 'license-update-check',
            });
        } catch (xhr) {
            this.set('checkStatus', LicenseCheckStatus.ERROR_CHECKING);

            return;
        }

        if (!checkRsp.canCheck) {
            /* There's nothing to do. */
            this.set('checkStatus', LicenseCheckStatus.HAS_LATEST);

            return;
        }

        const checkStatusURL = checkRsp.checkStatusURL;
        const requestData = checkRsp.data;
        const sessionToken = checkRsp.sessionToken || null;

        let data: (FormData | string) = null;

        if (typeof requestData === 'string') {
            data = requestData;
        } else if (requestData) {
            data = new FormData();

            for (const [key, value] of Object.entries(requestData)) {
                data.append(key, value as string);
            }
        }

        /* Send it to the configured endpoint. */
        let response: Response = null;
        let licenseRsp;

        try {
            const request: RequestInit = {
                body: data,
                method: 'POST',
            };

            if (checkRsp.credentials) {
                request.credentials = checkRsp.credentials;
            }

            if (checkRsp.headers) {
                request.headers = checkRsp.headers;
            }

            response = await fetch(checkStatusURL, request);

            const contentType = response.headers['content-type'].toLowerCase();

            if (contentType.startsWith('application/json') ||
                contentType.endsWith('+json')) {
                licenseRsp = await response.json();
            } else {
                licenseRsp = await response.text();
            }
        } catch (err) {
            /* Fall through and handle this below. */
            console.error('Error performing license check: %s', err);
            licenseRsp = null;
        }

        if (!licenseRsp || !response.ok) {
            this.onCheckForUpdatesHTTPError(response);

            return;
        }

        this.#processCheckForUpdatesResponse(
            licenseRsp,
            requestData,
            sessionToken);
    }

    /**
     * Handle HTTP errors when checking for updates.
     *
     * This will update the status of the license check depending on the error
     * code we get back.
     *
     * Subclasses can override this to provide custom error handling.
     *
     * By default, this will set the following values for ``checkStatus``:
     *
     * * :js:attr:`LicenseCheckStatus.NO_LICENSE` if the server returns a 403.
     * * :js:attr:`LicenseCheckStatus.ERROR_CHECKING` for any other error.
     *
     * Args:
     *     rsp (Response):
     *         The fetch response object.
     */
    onCheckForUpdatesHTTPError(response: Response) {
        if (response.status === 403) {
            /*
             * A 403 response from a license server indicates that there's
             * no accessible license.
             */
            this.set('checkStatus', LicenseCheckStatus.NO_LICENSE);
        } else {
            console.error('Error checking for license %o: response=%o',
                          this, response);

            this.set('checkStatus', LicenseCheckStatus.ERROR_CHECKING);
        }
    }

    /**
     * Process the response from checking for updates.
     *
     * This will pass the request and response payloads to the license
     * provider on the server, allowing it to handle the data as needed.
     * The result will be a new set of attributes to set on the license.
     *
     * Args:
     *     checkLicenseData (object):
     *         The license data received from the server.
     *
     *     options (CheckForUpdatesOptions):
     *         The options used for checking for updates.
     */
    async #processCheckForUpdatesResponse(
        checkLicenseData: object | string,
        requestData: object,
        sessionToken: string | null,
    ) {
        this.set('checkStatus', LicenseCheckStatus.APPLYING);

        let rsp: CheckUpdatesProcessResponsePayload;

        try {
            rsp = await this.callAction({
                action: 'process-license-update',
                args: {
                    check_request_data: requestData,
                    check_response_data: checkLicenseData,
                    session_token: sessionToken,
                },
            }) as CheckUpdatesProcessResponsePayload;
        } catch (xhr) {
            const responseText = xhr.responseText;

            console.error(
                'Error processing license %o response %o: rsp=%o, ' +
                'textStatus=%o',
                this, checkLicenseData, responseText, xhr.statusText);

            this.set('checkStatus', LicenseCheckStatus.ERROR_APPLYING);

            return;
        }

        /* The call succeeded. Notify the UI and listeners. */
        if (rsp.license_infos) {
            /*
             * There's new license information. We'll set this on all affected
             * licenses, set the status, and notify listeners of updates.
             *
             * This should be the common case.
             */
            const collection = this.collection as unknown as LicenseCollection;

            collection.updateLicenses(rsp.license_infos, {
                checkStatus: rsp.status,
            });
        } else {
            /*
             * There's no license data. We'll set the status on this license
             * and notify if this is marked as applied.
             */
            this.set('checkStatus', rsp.status);

            if (rsp.status === LicenseCheckStatus.APPLIED) {
                this.trigger('licenseUpdated');
            }
        }
    }
}
