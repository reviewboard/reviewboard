from django.dispatch import Signal


review_request_published = Signal(providing_args=["user", "review_request",
                                                  "changedesc"])

review_request_closed = Signal(providing_args=["user", "review_request",
                                               "type"])

review_request_reopened = Signal(providing_args=["user", "review_request"])


review_published = Signal(providing_args=["user", "review"])

reply_published = Signal(providing_args=["user", "reply"])
