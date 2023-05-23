.. _js-review-dialog-comment-hook:

=======================
ReviewDialogCommentHook
=======================

:js:class:`RB.ReviewDialogCommentHook` is used to add additional fields or
information to the comments shown in the Review Dialog. The hook is
instantiated with a ``viewType`` option that expects a custom Backbone.js_
view class, which is your custom view for modifying the comments in
the Review Dialog.

The view should inherit from :backbonejs:`View` (or a subclass of this), and
its model will be set to the same comment model (:js:class:`RB.DiffComment`,
:js:class:`RB.FileAttachmentComment`, or :js:class:`RB.GeneralComment`) used by
the comment. The view's element will be appended to the list of fields for
the comment.

It will also be bound to the same element as the comment in the Review Dialog,
allowing you to perform queries and modifications to ``this.$el``.

The view should not modify other fields for the comment.


Example
=======

.. code-block:: javascript

    const MyReviewDialogCommentHookView = Backbone.View.extend({
        events: {
            'change input': '_onInputChanged'
        },

        render() {
            this.extraData = this.model.get('extraData')['my-extension-id'];
            this.$input = $('<input type="text"/>')
                .val(this.extraData.myValue)
                .appendTo(this.$el);

            return this;
        },

        _onInputChanged() {
            this.extraData.myValue = this.$input.val();
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize() {
            RB.Extension.prototype.initialize.call(this);

            new RB.ReviewDialogCommentHook({
                extension: this,
                viewType: MyReviewDialogCommentHookView
            });
        }
    });


.. _Backbone.js: http://backbonejs.org/
