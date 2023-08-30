/** The draft file attachment resource model. */

import { spina } from '@beanbag/spina';

import { DraftResourceChildModelMixin } from './draftResourceChildModelMixin';
import { FileAttachment } from './fileAttachmentModel'


/**
 * A file attachment that's part of a draft.
 */
@spina({
    mixins: [DraftResourceChildModelMixin],
    prototypeAttrs: [
        'rspNamespace',
    ],
})
export class DraftFileAttachment extends FileAttachment {
    static rspNamespace = 'draft_file_attachment';
}
