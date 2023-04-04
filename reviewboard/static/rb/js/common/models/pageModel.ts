/**
 * Base class for page models.
 */
import { BaseModel, ModelAttributes, spina } from '@beanbag/spina';

/**
 * Base class for page models.
 *
 * This doesn't provide any functionality by itself, but may be used in the
 * future for introducing additional logic for pages.
 *
 * This is intended for use by page views that are set by
 * :js:class:`RB.PageManager`.
 */
@spina
export class Page<
    TDefaults extends ModelAttributes = ModelAttributes,
    TExtraModelOptions = unknown
> extends BaseModel<TDefaults, TExtraModelOptions> {
}
