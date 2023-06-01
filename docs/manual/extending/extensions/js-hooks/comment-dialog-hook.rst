.. _js-comment-dialog-hook:

=================
CommentDialogHook
=================

:js:class:`RB.CommentDialogHook` is used to add additional fields or
information to the Comment Dialog. The hook is instantiated with a
``viewType`` option that expects a custom Backbone.js_ view class, which is
your custom view for modifying the Comment Dialog.

The view should inherit from :backbonejs:`View` (or a subclass of this), and
will take the following options:

``commentDialog``:
    The instance of the :js:class:`RB.CommentDialogView`, which manages the
    UI of the Comment Dialog.

``commentEditor``:
    The instance of the :js:class:`RB.CommentEditor` model, which handles
    logic, storage, and API access for the comment.

It will also be bound to the same element as the Comment Dialog, allowing you
to perform queries and modifications to ``this.$el``.

Consumers of this hook must take care to code defensively, as some of the
structure of the Comment Dialog's DOM elements may change in future releases.


Example
=======

.. code-block:: javascript

    const MyCommentDialogHookView = Backbone.View.extend({
        initialize(options) {
            this.commentDialog = options.commentDialog;
            this.commentEditor = options.commentEditor;
        },

        render() {
            const $options = this.$('.comment-dlg-options');
            const $buttons = this.$('.comment-dlg-footer .buttons');

            $options.append('<li>Hi!</li>');
            $buttons.append('<button>Goodbye!</button>');
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize() {
            RB.Extension.prototype.initialize.call(this);

            new RB.CommentDialogHook({
                extension: this,
                viewType: MyCommentDialogHookView
            });
        }
    });

.. _Backbone.js: http://backbonejs.org/
