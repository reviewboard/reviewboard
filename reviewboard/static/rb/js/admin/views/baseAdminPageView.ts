/**
 * The base page view class for admin UI pages.
 */

import { spina } from '@beanbag/spina';

import {
    type Page,
    PageView as PageView,
} from 'reviewboard/common';
import {
    type PageViewOptions,
} from 'reviewboard/common/views/pageView';


/**
 * The base page view class for admin UI pages.
 */
@spina
export class BaseAdminPageView<
    TModel extends Page = Page,
    TElement extends HTMLBodyElement = HTMLBodyElement,
    TExtraViewOptions extends PageViewOptions = PageViewOptions
> extends PageView<TModel, TElement, TExtraViewOptions> {
}
