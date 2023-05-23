.. _js-review-dialog-hook:

================
ReviewDialogHook
================

:js:class:`RB.ReviewDialogHook` is used to add additional fields or
information to the top of the Review Dialog (around the :guilabel:`Ship It!`
area). The hook is instantiated with a ``viewType`` option that expects a
custom Backbone.js_ view class, which is your custom view for modifying the
Review Dialog.

The view should inherit from :backbonejs:`View` (or a subclass of this), and
its model will be set to the :js:class:`RB.Review` model being modified. The
view's element will be added in-between the :guilabel:`Ship It!` checkbox and
the Review body field.

It will also be bound to the same element as the Review Dialog, allowing you
to perform queries and modifications to ``this.$el``.


Example
=======

.. code-block:: javascript

    const MyReviewDialogHookView = Backbone.View.extend({
        events: {
            'change input': '_onCheckboxToggled'
        },

        render() {
            this.extraData = this.model.get('extraData')['my-extension-id'];
            this.$input = $('<input type="checkbox"/>')
                .prop('checked', this.extraData.myBool)
                .appendTo(this.$el);

            return this;
        },

        _onCheckboxToggled() {
            this.extraData.myBool = this.$input.prop('checked');
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize() {
            RB.Extension.prototype.initialize.call(this);

            new RB.ReviewDialogHook({
                extension: this,
                viewType: MyReviewDialogHookView
            });
        }
    });


.. _Backbone.js: http://backbonejs.org/
