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

    /** Extra data provided for the action handler. */
    extraData?: Record<string, unknown>;

    /** The URL to perform this action. */
    url?: string;
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
    lineItems?: string[] | null;

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
@spina
export class License<
    TAttrs extends LicenseAttrs = LicenseAttrs,
    TExtraOptions extends LicenseOptions = LicenseOptions,
    TOptions = Backbone.ModelSetOptions,
> extends BaseModel<TAttrs, TExtraOptions, TOptions> {
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
}
