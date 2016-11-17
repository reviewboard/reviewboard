.. _js-review-dialog-comment-hook:

=======================
ReviewDialogCommentHook
=======================

:js:class:`RB.ReviewDialogCommentHook` is used to add additional fields or
information to the comments shown in the review dialog. The hook is
instantiated with a ``viewType`` option that expects a custom Backbone.js_
view class, which is your custom view for modifying the comment dialog.

The view should inherit from :backbonejs:`View` (or a subclass of this), and
its model will be set to the same comment model (:js:class:`RB.DiffComment` or
:js:class:`FileAttachmentComment`) used by the comment. The view's element
will be appended to the list of fields for the comment.

The view should not modify other fields for the comment.


Example
=======

.. code-block:: javascript

    var MyReviewDialogCommentHookView = Backbone.View.extend({
        events: {
            'change input': '_onInputChanged'
        },

        render: function() {
            this.extraData = this.model.get('extraData')['my-extension-id'];
            this.$input = $('<input type="text"/>')
                .val(extraData.myValue)
                .appendTo(this.$el);

            return this;
        },

        _onInputChanged: function() {
            this.extraData.myValue = this.$input.val();
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize: function() {
            RB.Extension.initialize.call(this);

            new RB.ReviewDialogCommentHook({
                extension: this,
                viewType: MyReviewDialogCommentHookView
            });
        }
    });


.. _Backbone.js: http://backbonejs.org/
