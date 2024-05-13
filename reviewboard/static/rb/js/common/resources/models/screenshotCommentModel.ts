/**
 * A comment on a screenshot.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import * as JSONSerializers from '../utils/serializers';
import {
    type BaseCommentAttrs,
    type BaseCommentResourceData,
    BaseComment,
} from './baseCommentModel';
import {
    type SerializerMap,
} from './baseResourceModel';


/**
 * Attributes for the ScreenshotComment model.
 *
 * Version Added:
 *     8.0
 */
export interface ScreenshotCommentAttrs extends BaseCommentAttrs {
    /** height of the comment region, in pixels. */
    height: number | null;

    /** Screenshot that this comment is on. */
    screenshot: RB.Screenshot | null;

    /** ID of the screenshot that this comment is on. */
    screenshotID: number | null;

    /** URL to an image file showing the region of the comment. */
    thumbnailURL: string;

    /** width of the comment region, in pixels. */
    width: number | null;

    /** X coordinate of the pixel at the top-left of the comment region. */
    x: number | null;

    /** Y coordinate of the pixel at the top-left of the comment region. */
    y: number | null;
}


/**
 * Resource data for the ScreenshotComment model.
 *
 * Version Added:
 *     8.0
 */
export interface ScreenshotCommentResourceData
extends BaseCommentResourceData {
    h: number;
    screenshot: unknown; // TODO TYPING: future ScreenshotResourceData
    screenshotID: number;
    thumbnailURL: string;
    w: number;
    x: number;
    y: number;
}


/**
 * A comment on a screenshot.
 */
@spina
export class ScreenshotComment extends BaseComment<
    ScreenshotCommentAttrs,
    ScreenshotCommentResourceData
> {
    static defaults: Result<Partial<ScreenshotCommentAttrs>> = {
        height: null,
        screenshot: null,
        screenshotID: null,
        thumbnailURL: null,
        width: null,
        x: null,
        y: null,
    };

    static rspNamespace = 'screenshot_comment';
    static expandedFields = ['screenshot'];

    static attrToJsonMap: Record<string, string> = {
        height: 'h',
        screenshotID: 'screenshot_id',
        thumbnailURL: 'thumbnail_url',
        width: 'w',
    };

    static serializedAttrs = [
        'x',
        'y',
        'width',
        'height',
        'screenshotID',
    ].concat(super.serializedAttrs);

    static deserializedAttrs = [
        'x',
        'y',
        'width',
        'height',
        'thumbnailURL',
    ].concat(super.deserializedAttrs);

    static serializers: SerializerMap = {
        screenshotID: JSONSerializers.onlyIfUnloaded,
    };

    static strings = {
        INVALID_HEIGHT: 'height must be > 0',
        INVALID_SCREENSHOT_ID: 'screenshotID must be a valid ID',
        INVALID_WIDTH: 'width must be > 0',
        INVALID_X: 'x must be >= 0',
        INVALID_Y: 'y must be >= 0',
    };

    /**
     * Deserialize comment data from an API payload.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(
        rsp: ScreenshotCommentResourceData,
    ): Partial<ScreenshotCommentAttrs> {
        const result = super.parseResourceData(rsp);

        result.screenshot = new RB.Screenshot(rsp.screenshot, {
            parse: true,
        });
        result.screenshotID = result.screenshot.id;

        return result;
    }

    /*
     * Validate the attributes of the model.
     *
     * This will check the screenshot ID and the region of the comment,
     * along with the default comment validation.
     *
     * Args:
     *     attrs (object):
     *         The model attributes to validate.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(
        attrs: Partial<ScreenshotCommentAttrs>,
    ): string {
        if (attrs.hasOwnProperty('screenshotID') && !attrs.screenshotID) {
            return ScreenshotComment.strings.INVALID_SCREENSHOT_ID;
        }

        if (attrs.hasOwnProperty('x') && attrs.x < 0) {
            return ScreenshotComment.strings.INVALID_X;
        }

        if (attrs.hasOwnProperty('y') && attrs.y < 0) {
            return ScreenshotComment.strings.INVALID_Y;
        }

        if (attrs.hasOwnProperty('width') && attrs.width <= 0) {
            return ScreenshotComment.strings.INVALID_WIDTH;
        }

        if (attrs.hasOwnProperty('height') && attrs.height <= 0) {
            return ScreenshotComment.strings.INVALID_HEIGHT;
        }

        return super.validate(attrs);
    }
}
