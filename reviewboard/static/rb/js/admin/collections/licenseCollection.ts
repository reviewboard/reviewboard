/**
 * A collection of licenses.
 *
 * Version Added:
 *     7.1
 */
import {
    BaseCollection,
    spina,
} from '@beanbag/spina';

import {
    type LicenseCheckStatus,
    License,
} from '../models/licenseModel';


/**
 * Options for updating licenses.
 *
 * Version Added:
 *     7.1
 */
interface UpdateLicensesOptions {
    /**
     * An option ``checkStatus`` value to set on each updated license.
     */
    checkStatus?: LicenseCheckStatus;
}


/**
 * A collection of licenses.
 *
 * This manages a collection of licenses from the same License Provider, and
 * is used for updating batches of licenses or triggering sequential update
 * checks.
 *
 * Version Added:
 *     7.1
 */
@spina
export class LicenseCollection extends BaseCollection<License> {
    static model = License;

    /**
     * Check for updates to each license in the collection.
     *
     * License checks will be handled one-by-one. All errors will be handled
     * gracefully.
     */
    async checkForUpdates() {
        for (const license of this) {
            try {
                await license.checkForUpdates();
            } catch (err) {
                console.error('Update check for license "%s" failed: %s',
                              license.id, err);
            }
        }
    }

    /**
     * Update attributes for a batch of licenses in the collection.
     *
     * Any licenses found in ``licenseInfos`` that are not present in the
     * collection will be added. Any that exist will be updated. If any
     * are set to ``null``, they will be removed from the collection.
     *
     * This will trigger ``licenseUpdated`` events on any added or updated
     * licenses, and ``remove`` events on any removed licenses.
     *
     * Args:
     *     licenseInfos (object):
     *         A mapping of license IDs to either parsable license information
     *         or ``null``.
     *
     *     options (UpdateLicenseOptions, optional):
     *         Options to control the license updates.
     */
    updateLicenses(
        licenseInfos: Record<string, unknown>,
        options: UpdateLicensesOptions = {},
    ) {
        const checkStatus = options?.checkStatus;

        /* Gather all licenses we want to add, update, or remove. */
        const toRemove: string[] = [];
        const toSet: unknown[] = [];

        for (const [licenseID, licenseInfo] of Object.entries(licenseInfos)) {
            if (licenseInfo === null) {
                toRemove.push(licenseID);
            } else {
                toSet.push(licenseInfo);
            }
        }

        /*
         * Remove any removed licenses.
         *
         * This will trigger ``remove`` signals for these licenses.
         */
        if (toRemove.length > 0) {
            this.remove(toRemove);
        }

        /* Add or update any applicable licenses. */
        if (toSet.length > 0) {
            this.set(toSet, {
                parse: true,
                remove: false,
            });
        }

        /* Notify all signal handlers. */
        for (const licenseID of Object.keys(licenseInfos)) {
            const license = this.get(licenseID);

            if (license) {
                if (checkStatus) {
                    license.set('checkStatus', checkStatus);
                }

                license.trigger('licenseUpdated');
            }
        }
    }
}
