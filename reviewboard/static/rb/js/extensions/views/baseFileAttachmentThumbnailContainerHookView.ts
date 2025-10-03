/**
 * Base support for custom File Attachment Thumbnail Container hook views.
 *
 * Version Added:
 *     7.1
 */

import * as Backbone from 'backbone';
import {
    type BaseModel,
    BaseView,
    spina,
} from '@beanbag/spina';

import { type FileAttachment } from 'reviewboard/common';
import { type FileAttachmentThumbnailView } from 'reviewboard/reviews';
import { type Extension } from '../models/extensionModel';


/**
 * Options for BaseFileAttachmentThumbnailContainerHookView.
 *
 * Version Added:
 *     7.1
 */
export interface FileAttachmentThumbnailContainerHookViewOptions
extends Backbone.ViewOptions {
    /** The extension that owns the hook. */
    extension: Extension;

    /** The file attachment being rendered. */
    fileAttachment: FileAttachment;

    /** The thumbnail view managing the thumbnail. */
    thumbnailView: FileAttachmentThumbnailView;
}


/**
 * A base view for rendering into the file attachment thumbnail container.
 *
 * This is intended to be subclassed and passed in a view type to
 * :js:class:`RB.FileAttachmentThumbnailView`. It takes in the parent
 * extension and can then render into the container or hook into behavior.
 *
 * Version Added:
 *     7.1
 */
@spina
export class BaseFileAttachmentThumbnailContainerHookView extends BaseView<
    BaseModel,
    HTMLDivElement,
    unknown,
    FileAttachmentThumbnailContainerHookViewOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /** The extension that owns the hook. */
    extension: Extension;

    /** The file attachment being rendered. */
    fileAttachment: FileAttachment;

    /** The thumbnail view managing the thumbnail. */
    thumbnailView: FileAttachmentThumbnailView;

    /**
     * Pre-initialize the view.
     *
     * This will set the instance attributes based on the options provided
     * before the subclass's initialization code runs.
     *
     * Args:
     *     options (FileAttachmentThumbnailContainerHookViewOptions):
     *         The options for the view.
     */
    preinitialize(
        options: Partial<FileAttachmentThumbnailContainerHookViewOptions>,
    ) {
        this.extension = options.extension;
        this.fileAttachment = options.fileAttachment;
        this.thumbnailView = options.thumbnailView;
    }
}


/**
 * A type representing a BaseFileAttachmentThumbnailContainerHookView class.
 *
 * This types the constructor of the class such that it will properly return
 * an instance that is typed with the right constructor arguments and default
 * generics.
 *
 * Version Added:
 *     7.1
 */
export type BaseFileAttachmentThumbnailContainerHookViewClass =
    new (options: FileAttachmentThumbnailContainerHookViewOptions) =>
    BaseFileAttachmentThumbnailContainerHookView;
