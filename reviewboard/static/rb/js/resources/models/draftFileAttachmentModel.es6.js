/**
 * A file attachment that's part of a draft.
 */
RB.DraftFileAttachment = RB.FileAttachment.extend(_.defaults({
    rspNamespace: 'draft_file_attachment'
}, RB.DraftResourceChildModelMixin));
