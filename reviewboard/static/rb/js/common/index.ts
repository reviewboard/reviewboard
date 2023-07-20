/**
 * Library for the base-level state and functionality for Review Board.
 *
 * Version Added:
 *     6.0
 */


/**
 * An interface defining the structure of enabled feature maps.
 *
 * Version Added:
 *     6.0
 */
interface EnabledFeaturesInfo {
    [featureName: string]: boolean;
}


/**
 * An interface defining the product information for Review Board.
 *
 * Version Added:
 *     6.0
 */
interface ProductInfo {
    /** Whether this version of Review Board is a released build. */
    isRelease: boolean;

    /** The URL to the root of the Review Board manual for this version. */
    manualURL: string;

    /** The name of the product. */
    name: string;

    /** The version number of the product. */
    version: string;

    /**
     * The parsed version information.
     *
     * This is in the form of:
     *
     * Tuple:
     *     0 (number):
     *         The major version.
     *
     *     1 (number):
     *         The minor version.
     *
     *     2 (number):
     *         The micro version.
     *
     *     3 (number):
     *         The patch version.
     *
     *     4 (number):
     *         The release tag (``alpha``, ``beta``, ``rc``).
     *
     *     5 (number):
     *         The release number.
     */
    versionInfo: [number, number, number, number, string, number];
}


/**
 * A mapping of enabled features.
 *
 * Each key corresponds to a feature ID, and each value is set to ``true``.
 *
 * This is filled in on page load. It's empty by default.
 *
 * Version Added:
 *     3.0
 */
export const EnabledFeatures: EnabledFeaturesInfo = {};


/**
 * Information on the running version of Review Board.
 *
 * This is filled in on page load. It's set to mostly blank values by default.
 *
 * Version Added:
 *     4.0
 */
export const Product: ProductInfo = {
    isRelease: false,
    manualURL: '',
    name: 'Review Board',
    version: '',
    versionInfo: [0, 0, 0, 0, '', 0],
};


export * from './actions';
export * from './resources';
export { BaseCollection } from './collections/baseCollection';
export { ClientCommChannel } from './models/commChannelModel';
export { ExtraData } from './models/extraDataModel';
export { ExtraDataMixin } from './models/extraDataMixin';
export { Page } from './models/pageModel';
export { PageView } from './views/pageView';
export { UserSession } from './models/userSessionModel';
