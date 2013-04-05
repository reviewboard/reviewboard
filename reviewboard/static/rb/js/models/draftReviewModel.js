/*
 * Draft reviews.
 *
 * Draft reviews are more complicated than most objects. A draft may already
 * exist on the server, in which case we need to be able to get its ID. A
 * special resource exists at /reviews/draft/ which will redirect to the
 * existing draft if one exists, and return 404 if not.
 */
RB.DraftReview = RB.Review.extend(RB.DraftResourceModelMixin);
