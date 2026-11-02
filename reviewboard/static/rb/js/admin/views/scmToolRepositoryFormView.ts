/**
 * Base view for SCMTool behavior in the repository form.
 *
 * Version Added:
 *     9.0
 */

import {
    BaseView,
    spina,
} from '@beanbag/spina';

import { type RepositoryForm } from '../models/repositoryFormModel';


/**
 * Base view for SCMTool behavior in the repository form.
 *
 * The repository form creates one of these when an SCMTool is selected
 * without a hosting service, and removes it when that changes. The view's
 * element is the whole form, so subclasses can listen to any field.
 *
 * SCMTools can subclass this and set the class name in their
 * ``repository_form_js_view_class`` attribute.
 *
 * Version Added:
 *     9.0
 */
@spina
export class SCMToolRepositoryFormView extends BaseView<
    RepositoryForm,
    HTMLFormElement
> {
    /**
     * Detach the view from the form.
     *
     * The form is shared with the main repository form view, so only the
     * event handlers are removed. The element is left in place.
     */
    _removeElement() {
        this.undelegateEvents();
    }
}
