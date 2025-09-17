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
    ButtonType,
    craft,
    paint,
    renderInto,
} from '@beanbag/ink';
import { spina } from '@beanbag/spina';
import { dedent } from 'babel-plugin-dedent';

import {
    type LicenseCollection,
} from '../collections/licenseCollection';
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

    /** CSS class name for an icon to show alongside the content. */
    iconName?: string;
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
@spina({
    prototypeAttrs: ['actionBuilders'],
})
export class LicenseView<
    TModel extends License = License,
> extends BaseComponentView<TModel> {
    static className = 'rb-c-license';

    static modelEvents = {
        'change:checkStatus': '_onCheckStatusChanged',
        'licenseUpdated': 'render',
        'remove': 'remove',
    };

    /**
     * A mapping of action IDs to builder functions for action rendering.
     *
     * Subclasses can override this to provide special rendering and
     * handling for actions.
     */
    static actionBuilders: Record<string, string> = {
        'upload-license': '_buildUploadLicenseActionButton',
    };
    actionBuilders: Record<string, string>;

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
     *         The item or items to use for the contents of the details row.
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
        const iconName = options.iconName || '';

        attrs.class = 'rb-c-license__detail';

        if (className) {
            attrs.class += ` ${className}`;
        }

        renderInto(this.#detailsEl, paint`
            <li ...${attrs}>
             <span class="rb-c-license__detail-icon ${iconName}"/>
             <div class="rb-c-license__detail-content">
              ${item}
             </div>
            </li>
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

            this.addLicenseDetail(paint([expiresHTML]), {
                iconName: expiresIcon,
            });
        }

        for (const lineItem of lineItems) {
            this.addLicenseDetail(
                (lineItem.contentIsHTML
                 ? paint([lineItem.content])
                 : lineItem.content),
                {
                    iconName: lineItem.icon,
                });
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
        const actionBuilders = this.actionBuilders;

        const actionEls = actions.map(actionInfo => {
            const builderFuncName = actionBuilders[actionInfo.actionID];
            const builderFunc = (builderFuncName
                                 ? this[builderFuncName]
                                 : buildActionButton);

            return builderFunc.call(this, actionInfo);
        });

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
                  ${actionEls}
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
     * By default, actions will result in action calls to the License
     * Provider. These can return a ``license_infos`` with a list of license
     * changes, and can return a ``redirect_url`` with a URL to navigate to.
     *
     * Args:
     *     options (LicenseActionHandlerOptions):
     *         Options for the action invocation.
     */
    protected async onAction(options: LicenseActionHandlerOptions) {
        try {
            const rsp = await this.model.callAction({
                action: options.actionID,
                args: options.actionInfo.callArgs,
            }) as Record<string, unknown>;
        } catch (err) {
            console.error('Unexpected error performing license action: %s',
                          err);

            /* Show the error to the user. */
            alert(`There was an error performing this action: ${err.message}`);

            return;
        }

        if (rsp.license_infos) {
            const collection = this.collection as unknown as LicenseCollection;

            collection.updateLicenses(
                rsp.license_infos as Record<string, unknown>);
        }

        if (rsp.redirect_url) {
            RB.navigateTo(rsp.redirect_url);
        }
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

        if (actionInfo.primary) {
            attrs.type = ButtonType.PRIMARY;
        }

        const actionButton = craft<ButtonView>`
            <Ink.Button ...${attrs}>
             ${actionInfo.label}
            </Ink.Button>
        `;

        return actionButton;
    }

    /**
     * Build the Upload License action elements.
     *
     * This will build the action and upload field, and handle all
     * interactions and UI updates for the upload process.
     *
     * Args:
     *     actionInfo (LicenseAction):
     *         Information for the action.
     *
     * Returns:
     *     HTMLElement[]:
     *     The resulting action elements.
     */
    private _buildUploadLicenseActionButton(
        actionInfo: LicenseAction,
    ): HTMLElement[] {
        const buttonLabel = actionInfo.label;
        const fileFieldID = `license-upload-form-field-${this.cid}`;

        function resetButton() {
            button.busy = false;
            button.label = buttonLabel;
        }

        function onClick() {
            button.busy = true;
            button.label = _`Selecting license file...`;
            fileFieldEl.click();
        }

        const button = craft<ButtonView>`
            <Ink.Button onClick=${onClick}>
             ${buttonLabel}
            </Ink.Button>
        `;

        const fileFieldEl = paint<HTMLInputElement>`
            <input id="${fileFieldID}"
                   name="license_data"
                   type="file"
                   style="display: none"/>
        `;
        fileFieldEl.addEventListener('cancel', () => resetButton());
        fileFieldEl.addEventListener('change', async () => {
            /* Handle the file upload. */
            const file = fileFieldEl.files[0];

            /*
             * Just a quick sanity-check before we start uploading content.
             */
            console.assert(file.size < 1000000);

            button.label = _`Uploading license file...`;

            try {
                await this.model.uploadLicenseFile(file);
            } catch (err) {
                alert(err.message);
            }

            resetButton();
        });

        return paint<HTMLElement[]>`
            ${fileFieldEl}
            <label htmlFor="${fileFieldID}">
             ${button}
            </label>
        `;
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
