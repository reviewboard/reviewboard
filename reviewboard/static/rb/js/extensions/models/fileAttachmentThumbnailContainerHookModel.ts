/**
 * Extension hook for extending file attachment thumbnails.
 *
 * Version Changed:
 *     7.1:
 *     This is now an ESM module supporting TypeScript.
 */

import { spina } from '@beanbag/spina';

import {
    type ExtensionHookAttrs,
    ExtensionHook,
} from './extensionHookModel';
import { ExtensionHookPoint } from './extensionHookPointModel';
import {
    type BaseFileAttachmentThumbnailContainerHookViewClass,
} from '../views/baseFileAttachmentThumbnailContainerHookView';


/**
 * Attributes for FileAttachmentThumbnailContainerHook.
 *
 * Version Added:
 *     7.1
 */
export interface FileAttachmentThumbnailContainerHookAttrs
extends ExtensionHookAttrs {
    /** The view type to construct to modify the thumbnail view. */
    viewType: BaseFileAttachmentThumbnailContainerHookViewClass;
}


/**
 * Provides extensibility for File Attachment thumbnails.
 *
 * This can be used to display additional UI on file attachment containers
 * and on the file attachment actions menu. This should not be used to create
 * or modify the thumbnail image itself, use :py:class:`~reviewboard
 * .extensions.hooks.FileAttachmentThumbnailHook` for that behavior instead.
 *
 * Users of this hook must provide a Backbone View (not an instance) which
 * will modify the File Attachment thumbnail. The view will have access to
 * the FileAttachmentThumbnailView and its FileAttachment model (through
 * the thumbnailView and fileAttachment options passed to the view).
 *
 * Version Changed:
 *     7.1:
 *     This is now a modern ES6-style class and supports typing using
 *     TypeScript.
 *
 * Version Added:
 *     6.0
 */
@spina
export class FileAttachmentThumbnailContainerHook<
    TAttrs extends FileAttachmentThumbnailContainerHookAttrs =
        FileAttachmentThumbnailContainerHookAttrs,
> extends ExtensionHook<TAttrs> {
    static hookPoint = new ExtensionHookPoint();

    static defaults: Partial<FileAttachmentThumbnailContainerHookAttrs> = {
        viewType: null,
    };

    /**
     * Set up the hook.
     */
    setUpHook() {
        console.assert(this.get('viewType'),
                       'FileAttachmentThumbnailContainerHook instance does ' +
                       'not have a "viewType" attribute set.');
    }
}
