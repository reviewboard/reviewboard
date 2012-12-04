from reviewboard.reviews.ui.base import FileAttachmentReviewUI


class ImageReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/*']
    template_name = 'reviews/ui/image.html'
    object_key = 'image'

    def serialize_comments(self, comments):
        result = {}

        for comment in comments:
            try:
                position = '%(x)sx%(y)s+%(width)s+%(height)s' \
                           % comment.extra_data
            except KeyError:
                # It's possible this comment was made before the review UI
                # was provided, meaning it has no data. If this is the case,
                # ignore this particular comment, since it doesn't have a
                # region.
                continue

            result.setdefault(position, []).append(
                self.serialize_comment(comment))

        return result
