.. _js-review-dialog-hook:

================
ReviewDialogHook
================

:js:class:`RB.ReviewDialogHook` is used to add additional fields or
information to the top of the review dialog (aroud the :guilabel:`Ship It!`
area). The hook is instantiated with a ``viewType`` option that expects a
custom Backbone.js_ view class, which is your custom view for modifying the
comment dialog.

The view should inherit from :backbonejs:`View` (or a subclass of this), and
its model will be set to the :js:class:`RB.Review` model being modified. The
view's element will be added in-between the :guilabel:`Ship It!` checkbox and
the review body field.

The view should not modify other fields for the comment.


Example
=======

.. code-block:: javascript

    var MyReviewDialogHookView = Backbone.View.extend({
        events: {
            'change input': '_onCheckboxToggled'
        },

        render: function() {
            this.extraData = this.model.get('extraData')['my-extension-id'];
            this.$input = $('<input type="checkbox"/>')
                .prop('checked', extraData.myBool)
                .appendTo(this.$el);

            return this;
        },

        _onCheckboxToggled: function() {
            this.extraData.myBool = this.$input.prop('checked');
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize: function() {
            RB.Extension.initialize.call(this);

            new RB.ReviewDialogHook({
                extension: this,
                viewType: MyReviewDialogHookView
            });
        }
    });


.. _Backbone.js: http://backbonejs.org/
