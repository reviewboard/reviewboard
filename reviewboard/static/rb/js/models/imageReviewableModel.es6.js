/**
 * Provides review capabilities for image file attachments.
 *
 * Model Attributes:
 *     imageURL (string):
 *         The image URL.
 *
 *     diffAgainstImageURL (string):
 *         The image URL of the original image in the case of a image diff.
 *
 *     scale (number):
 *         The scale at which the image is being rendered.
 */
RB.ImageReviewable = RB.FileAttachmentReviewable.extend({
    defaults: _.defaults({
        imageURL: '',
        diffAgainstImageURL: '',
        scale: 1,
    }, RB.FileAttachmentReviewable.prototype.defaults),

    commentBlockModel: RB.RegionCommentBlock,
});
