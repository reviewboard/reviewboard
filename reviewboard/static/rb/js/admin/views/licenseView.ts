/**
 * View for managing a license.
 *
 * Version Added:
 *     7.1
 */

import {
    type ButtonView,
    type CraftedComponent,
    BaseComponentView,
    craft,
    paint,
    renderInto,
} from '@beanbag/ink';
import { spina } from '@beanbag/spina';
import { dedent } from 'babel-plugin-dedent';

import {
    type License,
    type LicenseAction,
    LicenseCheckStatus,
    LicenseStatus,
} from '../models/licenseModel';


/**
 * A mapping of license check statuses to localized description strings.
 *
 * Version Added:
 *     7.1
 */
const CHECK_STATUS_TEXT: Record<LicenseCheckStatus, string> = {
    [LicenseCheckStatus.NO_LICENSE]: _`
        The product is not licensed.
    `,
    [LicenseCheckStatus.CHECKING]: _`
        Checking for updates...
    `,
    [LicenseCheckStatus.HAS_LATEST]: _`
        Your license is up-to-date.
    `,
    [LicenseCheckStatus.APPLYING]: _`
        Applying license update...
    `,
    [LicenseCheckStatus.APPLIED]: _`
        Your license has been automatically updated.
    `,
    [LicenseCheckStatus.ERROR_CHECKING]: _`
        An error occurred when trying to check for license updates.
        Please contact support.
    `,
    [LicenseCheckStatus.ERROR_APPLYING]: _`
        An error occurred when trying to apply a new license.
        Please contact support.
    `,
};


/**
 * Options for adding a detail item for a license.
 *
 * Version Added:
 *     7.1
 */
export interface AddLicenseDetailOptions {
    /** HTML attributes for the item's container element. */
    attrs?: Record<string, string>;

    /** Extra class names for the item's container element. */
    className?: string;
}


/**
 * Options passed to a license action handler.
 *
 * Version Added:
 *     7.1
 */
export interface LicenseActionHandlerOptions {
    /** The ID of the action. */
    actionID: string;

    /** The registered information on the action. */
    actionInfo: LicenseAction;

    /** The button representing the action. */
    button: ButtonView;

    /** The click event on the button. */
    event: JQuery.ClickEvent;
}


/**
 * A view managing the display, state, and actions for a license.
 *
 * This shows the state of the license, whether it's active, expired, or
 * expiring soon. It lists the product, line items, and any specific
 * detail line items provided by a subclass.
 *
 * License views contain buttons that can be used to perform actions on a
 * license, such as managing a license or uploading new license data.
 *
 * Version Added:
 *     7.1
 */
@spina
export class LicenseView<
    TModel extends License = License,
> extends BaseComponentView<TModel> {
    static className = 'rb-c-license';

    static modelEvents = {
        'change:checkStatus': '_onCheckStatusChanged',
        'licenseUpdated': 'render',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The element storing additional details for the license. */
    #detailsEl: HTMLElement;

    /** The element showing license state. */
    #stateEl: HTMLElement;

    /**
     * Add a row of details to the license.
     *
     * The content and display of the details is up to the caller.
     *
     * Args:
     *     item (string or Node or Ink.CraftedComponent or Array):
     *         The item or items to use for the details row.
     *
     *     options (AddLicenseDetailOptions, optional):
     *         Options for the item.
     */
    addLicenseDetail(
        item: string | CraftedComponent | CraftedComponent[],
        options: AddLicenseDetailOptions = {},
    ) {
        const attrs = options.attrs || {};
        const className = options.className;

        attrs.class = 'rb-c-license__detail';

        if (className) {
            attrs.class += ` ${className}`;
        }

        renderInto(this.#detailsEl, paint`
            <li ...${attrs}>${item}</li>
        `);
    }

    /**
     * Handle rendering of the license.
     *
     * This will replace the entire contents of the license with a new
     * render, showing the current state and details for the license along
     * with any actions.
     */
    protected onRender() {
        const model = this.model;
        const actions = model.get('actions') || [];
        const expiresDate = model.get('expiresDate');
        const licenseStatus = model.get('status');
        const lineItems = model.get('lineItems') || [];
        const manageURL = model.get('manageURL');
        const noticeHTML = model.get('noticeHTML');
        const summary = model.get('summary');
        const warningHTML = model.get('warningHTML');

        /* Begin building the license details. */
        const detailsNodes = paint<HTMLUListElement>`
            <ul class="rb-c-license__details"/>
        `;
        this.#detailsEl = detailsNodes;

        /* Build the information on the license expiration. */
        if (licenseStatus !== LicenseStatus.UNLICENSED && expiresDate) {
            const expiresMoment = moment(expiresDate);
            const expirationTimestamp = expiresMoment.format();
            const expirationDate =
                expiresMoment.format('MMM. D, YYYY, h:mm A');
            let expiresHTML: string;
            let expiresIcon: string;

            const datetimeHTML = dedent`
                <time class="timesince"
                dateTime="${expirationTimestamp}"></time>
            `;

            if (licenseStatus === LicenseStatus.LICENSED) {
                expiresIcon = 'ink-i-info';
                expiresHTML = _`Expires ${datetimeHTML} on ${expirationDate}`;
            } else if (licenseStatus === LicenseStatus.HARD_EXPIRED) {
                expiresIcon = 'ink-i-warning';
                expiresHTML = _`Expired ${datetimeHTML} on ${expirationDate}`;
            } else if (licenseStatus === LicenseStatus.EXPIRED_GRACE_PERIOD) {
                const gracePeriodDaysRemaining =
                    model.get('gracePeriodDaysRemaining');

                expiresIcon = 'ink-i-warning';
                expiresHTML = _`
                    Expired ${datetimeHTML} on
                    ${expirationDate}. There are ${gracePeriodDaysRemaining}
                    days left on your grace period.
                `;
            } else {
                expiresIcon = 'ink-i-warning';
                expiresHTML = _`
                    Unknown expiration status. Please report this.
                `;
            }

            this.addLicenseDetail(paint`
                <span class="rb-c-license__detail-icon ${expiresIcon}"/>
                <div class="rb-c-license__detail-content">
                 ${paint([expiresHTML])}
                </div>
            `);
        }

        for (const lineItem of lineItems) {
            this.addLicenseDetail(lineItem);
        }

        /* Begin rendering the view. */
        const el = this.el;

        el.setAttribute('data-status', licenseStatus);

        if (warningHTML) {
            el.classList.add('-has-warning');
        }

        const stateEl = paint<HTMLElement>`
            <div class="rb-c-license__state"></div>
        `;
        this.#stateEl = stateEl;
        this._onCheckStatusChanged();

        const buildActionButton = this.#buildActionButton.bind(this);

        renderInto(
            el,
            paint`
                <div class="rb-c-license__header">
                 <h3 class="rb-c-license__summary">${summary}</h3>
                 ${warningHTML && paint`
                  <div class="rb-c-license__warning">
                   ${paint([warningHTML])}
                  </div>
                 `}
                 ${noticeHTML && paint`
                  <div class="rb-c-license__notice">
                   ${paint([noticeHTML])}
                  </div>
                 `}
                 ${stateEl}
                 <div class="rb-c-license__actions">
                  ${manageURL && paint`
                   <Ink.Button type="primary" tagName="a" href="${manageURL}">
                    ${_`Manage your license`}
                   </Ink.Button>
                  `}
                  ${actions.map(actionInfo => buildActionButton(actionInfo))}
                 </div>
                 ${detailsNodes}
                </div>
            `, {
                empty: true,
            });

        this.$('.timesince').timesince();
    }

    /**
     * Handle a license action.
     *
     * Subclasses can override it to provide handling of any custom actions.
     *
     * Args:
     *     options (LicenseActionHandlerOptions):
     *         Options for the action invocation.
     */
    protected onAction(options: LicenseActionHandlerOptions) {
        /* This function intentionally left blank. */
    }

    /**
     * Build an action button.
     *
     * Args:
     *     actionInfo (LicenseAction):
     *         Information for the action.
     *
     * Returns:
     *     Ink.ButtonView:
     *     The resulting action button.
     */
    #buildActionButton(
        actionInfo: LicenseAction,
    ): ButtonView {
        const attrs: Record<string, unknown> = {};

        if (actionInfo.url) {
            attrs.tagName = 'a';
            attrs.href = actionInfo.url;
        } else {
            attrs.onClick = (evt => this.onAction({
                actionID: actionInfo.actionID,
                actionInfo: actionInfo,
                button: actionButton,
                event: evt,
            }));
        }

        const actionButton = craft<ButtonView>`
            <Ink.Button ...${attrs}>
             ${actionInfo.label}
            </Ink.Button>
        `;

        return actionButton;
    }

    /**
     * Handle changes to the license status.
     *
     * This will update the display of the license and the status text to
     * reflect the current status.
     */
    private _onCheckStatusChanged() {
        const checkStatus = this.model.get('checkStatus') ||
                            LicenseCheckStatus.HAS_LATEST;

        this.el.setAttribute('data-check-status', checkStatus);

        this.#stateEl.innerText = CHECK_STATUS_TEXT[checkStatus] || '';
    }
}
