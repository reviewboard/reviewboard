/**
 * A default reviewer configuration.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    BaseResource,
} from './baseResourceModel';


/**
 * Attributes for the DefaultReviewer model.
 *
 * Version Added:
 *     7.0.1
 */
export interface DefaultReviewerAttrs extends BaseResourceAttrs {
    /** The regular expression to apply to filenames in diffs. */
    fileRegex: string;

    /** The name of the default reviewer rule. */
    name: string;
}


/**
 * Resource data for the DefaultReviewer model.
 *
 * Version Added:
 *     7.0.1
 */
export interface DefaultReviewerResourceData extends BaseResourceResourceData {
    file_regex: string;
    name: string;
}


/**
 * A default reviewer configuration.
 *
 * Default reviewers auto-populate the list of reviewers for a review request
 * based on the files modified.
 *
 * The support for default reviewers is currently limited to the most basic
 * information. The lists of users, repositories and groups cannot yet be
 * provided.
 */
@spina
export class DefaultReviewer extends BaseResource<
    DefaultReviewerAttrs,
    DefaultReviewerResourceData
> {
    static defaults: Result<Partial<DefaultReviewerAttrs>> = {
        fileRegex: null,
        name: null,
    };

    static rspNamespace = 'default_reviewer';

    static attrToJsonMap: Record<string, string> = {
        fileRegex: 'file_regex',
    };

    static serializedAttrs = ['fileRegex', 'name'];
    static deserializedAttrs = ['fileRegex', 'name'];

    /**
     * Return the URL for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to use when making HTTP requests.
     */
    url(): string {
        const localSitePrefix = this.get('localSitePrefix') || '';
        const url = `${SITE_ROOT}${localSitePrefix}api/default-reviewers/`;

        return this.isNew() ? url : `${url}${this.id}/`;
    }
}
