from reviewboard.reviews.ui.base import FileAttachmentReviewUI


class ImageReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/*']
    template_name = 'reviews/ui/image.html'
    object_key = 'image'

    def serialize_comments(self, comments):
        result = {}

        for comment in comments:
            position = '%(x)sx%(y)s+%(width)s+%(height)s' % comment.extra_data

            result.setdefault(position, []).append(
                self.serialize_comment(comment))

        return result
