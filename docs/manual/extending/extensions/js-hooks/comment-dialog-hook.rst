.. _js-comment-dialog-hook:

=================
CommentDialogHook
=================

:js:class:`RB.CommentDialogHook` is used to add additional fields or
information to the comment dialog. The hook is instantiated with a
``viewType`` option that expects a custom Backbone.js_ view class, which is
your custom view for modifying the comment dialog.

The view should inherit from :backbonejs:`View` (or a subclass of this), and
will take the following options:

``commentDialog``:
    The instance of the :js:class:`RB.CommentDialogView`, which manages the
    UI of the comment dialog.

``commentEditor``:
    The instance of the :js:class:`RB.CommentEditor` model, which handles
    logic, storage, and API access for the comment.

It will also be bound to the same element as the comment dialog, allowing you
to perform queries and modifications to ``this.$el``.

Consumers of this hook must take care to code defensively, as some of the
structure of the comment dialog's DOM elements may change in future releases.


Example
=======

.. code-block:: javascript

    var MyCommentDialogHookView = Backbone.View.extend({
        initialize: function(options) {
            this.commentDialog = options.commentDialog;
            this.commentEditor = options.commentEditor;
        },

        render: function() {
            var $options = this.$('.comment-dlg-options'),
                $buttons = this.$('.comment-dlg-footer .buttons');

            $options.append('<li>Hi!</li>');
            $buttons.append('<button>Goodbye!</button>');
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize: function() {
            RB.Extension.initialize.call(this);

            new RB.CommentDialogHook({
                extension: this,
                viewType: MyCommentDialogHookView
            });
        }
    });

.. _Backbone.js: http://backbonejs.org/
