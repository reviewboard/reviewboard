/**
 * Error for license action calls.
 *
 * Version Added:
 *     8.0
 */


/**
 * Options for CallLicenseActionError.
 *
 * Version Added:
 *     8.0
 */
export interface CallLicenseActionErrorOptions {
    /** The action that was called. */
    action: string;

    /** The target for the action. */
    actionTarget: string;

    /** An explicit error message to show. */
    message: string;

    /** The HTTP response from the request, if any. */
    response: Response | null;
}


/**
 * Error for license action calls.
 *
 * This can be thrown whenever a license action call fails, allowing the
 * handler to convey the error from the client or server and introspect any
 * API results.
 *
 * Version Added:
 *     8.0
 */
export class CallLicenseActionError extends Error {
    /**********************
     * Instance variables *
     **********************/

    /** The action that was called. */
    action: string;

    /** The target for the action. */
    actionTarget: string;

    /** The HTTP response from the request, if any. */
    response: Response | null;

    /**
     * Construct a new instance.
     *
     * This will store the information from the options and set either the
     * provided or a default error message.
     *
     * Args:
     *     options (CallLicenseActionErrorOptions):
     *         Options for the error.
     */
    constructor(options: CallLicenseActionErrorOptions) {
        const action = options.action;

        super(options.message ||
              `Error performing license action "${action}"`);

        this.action = action;
        this.actionTarget = options.actionTarget;
        this.response = options.response || null;
    }
}
