from django.dispatch import Signal


review_request_published = Signal(providing_args=["user", "review_request",
                                                  "changedesc"])

review_published = Signal(providing_args=["user", "review"])

reply_published = Signal(providing_args=["user", "reply"])
