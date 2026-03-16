/**
 * A screenshot.
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
 * Attributes for the Screenshot model.
 *
 * Version Added:
 *     8.0
 */
export interface ScreenshotAttrs extends BaseResourceAttrs {
    /** The screenshot's caption. */
    caption: string;

    /** The name of the file for the screenshot. */
    filename: string;

    /** The URL of the review UI for this screenshot. */
    reviewURL: string;
}


/**
 * Resource data for the Screenshot model.
 *
 * Version Added:
 *     8.0
 */
export interface ScreenshotResourceData extends BaseResourceResourceData {
    caption: string;
    filename: string;
    reviewURL: string;
}


/**
 * A screenshot.
 */
@spina
export class Screenshot extends BaseResource<
    ScreenshotAttrs,
    ScreenshotResourceData,
> {
    static defaults: Result<Partial<ScreenshotAttrs>> = {
        caption: null,
        filename: null,
        reviewURL: null,
    };

    static rspNamespace = 'screenshot';

    static attrToJsonMap: Record<string, string> = {
        reviewURL: 'review_url',
    };

    static serializedAttrs = ['caption'];
    static deserializedAttrs = ['caption', 'filename', 'reviewURL'];

    /**
     * Return a displayable name for the screenshot.
     *
     * This will return the caption, if one is set. Otherwise, the filename
     * is returned.
     *
     * Returns:
     *     string:
     *     A string to show in the UI.
     */
    getDisplayName(): string {
        return (this.get('caption') ||
                this.get('filename'));
    }
}
