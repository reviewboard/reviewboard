import { BaseView, spina } from '@beanbag/spina';

import { Action } from '../models/actionModel';


/**
 * Base view for actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ActionView<
    TModel extends Action = Action,
    TElement extends HTMLDivElement = HTMLDivElement,
    TExtraViewOptions extends object = object
> extends BaseView<TModel, TElement, TExtraViewOptions> {
}
