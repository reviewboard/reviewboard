/**
 * A resource for checking whether a diff will work.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type DiffAttrs,
    type DiffResourceData,
    Diff,
} from './diffModel';


/**
 * Attributes for the ValidateDiffModel.
 *
 * Version Added:
 *     8.0
 */
export interface ValidateDiffAttrs extends DiffAttrs {
    /** The local-site prefix to use for URLs. */
    localSitePrefix: string;

    /** The ID of the repository to validate the diff against. */
    repository: number;
}


/**
 * Resource data for the ValidateDiffModel.
 *
 * Version Added:
 *     8.0
 */
export interface ValidateDiffResourceData extends DiffResourceData {
    repository: number;
}


/**
 * A resource for checking whether a diff will work.
 *
 * This is meant to be used as a sort of throwaway object, since a POST to the
 * diff validation resource does not actually create any state on the server.
 *
 * To use this, create an instance of the model, and set the diff and
 * repository attributes. The parentDiff and basedir attributes can also be
 * set, in the cases where the diff file requires a parent diff, and when the
 * given repository requires base directory information, respectively.
 *
 * Once these are set, calling save() will do a server-side check to make sure
 * that the supplied files parse correctly, and that the source revisions are
 * present in the given repository. save's 'success' and 'error' callbacks can
 * be used to act upon this information.
 */
@spina
export class ValidateDiffModel extends Diff<
    ValidateDiffAttrs,
    ValidateDiffResourceData
> {
    static defaults: Result<Partial<ValidateDiffAttrs>> = {
        localSitePrefix: '',
        repository: null,
    };

    static serializedAttrs = [
        'repository',
    ].concat(super.serializedAttrs);

    /**
     * Return the URL to use when syncing this model.
     *
     * Returns:
     *     string:
     *     The URL to use for syncing.
     */
    url(): string {
        const localSitePrefix = this.get('localSitePrefix') || '';

        return `${SITE_ROOT}${localSitePrefix}api/validation/diffs/`;
    }

    /**
     * Parse the result from the server.
     *
     * This is a no-op for this resource.
     *
     * Args:
     *     rsp (ValidateDiffResourceData):
     *         The response from the server.
     *
     * Returns:
     *     ValidateDiffAttrs:
     *     Attributes to set on the model.
     */
    parse(
        rsp: Partial<ValidateDiffResourceData & { stat: string }>,
    ): Partial<ValidateDiffAttrs> {
        return {};
    }
}
