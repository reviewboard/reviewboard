/**
 * A view for managing the administration UI's database model change pages.
 *
 * This sets up the page to manage the configuration form and any inline
 * groups used for adding, modifying, or deleting related objects.
 */
RB.Admin.ChangeFormPageView = RB.Admin.PageView.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         The options passed to the page.
     *
     * Option Args:
     *     formID (string):
     *         The element ID for the form.
     */
    initialize(options) {
        RB.Admin.PageView.prototype.initialize.call(this, options);

        this.formID = options.formID;
        this.formView = null;
        this.inlineGroupViews = [];
    },

    /**
     * Render the page.
     *
     * This will set up the form and inline group management.
     */
    renderPage() {
        RB.Admin.PageView.prototype.renderPage.call(this);

        console.assert(this.inlineGroupViews.length === 0);

        this.formView = new RB.FormView({
            el: $(`#${this.formID}`),
        });
        this.formView.render();

        this.$('.rb-c-admin-form-inline-group').each((i, el) => {
            const inlineGroup = new RB.Admin.InlineFormGroup({
                prefix: $(el).data('prefix'),
            });
            const inlineGroupView = new RB.Admin.InlineFormGroupView({
                el: el,
                model: inlineGroup,
            });
            inlineGroupView.renderPage();

            this.inlineGroupViews.push(inlineGroupView);

            this.listenTo(
                inlineGroupView,
                'inlineFormAdded',
                () => this.formView.setupFormWidgets(inlineGroupView.$el));
        });
    },
});
