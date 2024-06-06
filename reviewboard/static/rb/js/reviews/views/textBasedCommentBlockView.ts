/**
 * View for comment blocks on text-based files.
 */

import { spina } from '@beanbag/spina';

import { type DiffCommentBlock } from '../models/diffCommentBlockModel';
import { type TextCommentBlock } from '../models/textCommentBlockModel';
import { AbstractCommentBlockView } from './abstractCommentBlockView';
import { type CommentDialogView } from './commentDialogView';


/**
 * View for comment blocks on text-based files.
 *
 * This will show a comment indicator flag (a "ghost comment flag") beside the
 * content indicating there are comments there. It will also show the
 * number of comments, along with a tooltip showing comment summaries.
 *
 * This is meant to be used with a TextCommentBlock model.
 */
@spina({
    prototypeAttrs: ['template'],
})
export class TextBasedCommentBlockView<
    TModel extends TextCommentBlock | DiffCommentBlock = TextCommentBlock,
    TElement extends Element = HTMLElement,
    TExtraViewOptions = unknown
> extends AbstractCommentBlockView<TModel, TElement, TExtraViewOptions> {
    static tagName = 'span';
    static className = 'commentflag';

    static template = _.template(dedent`
        <span class="commentflag-shadow"></span>
        <span class="commentflag-inner">
         <span class="commentflag-count"></span>
        </span>
        <a name="<%= anchorName %>" class="commentflag-anchor"></a>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The element for the starting row of the comment. */
    $beginRow: JQuery = null;

    /** The element for the ending row of the comment. */
    $endRow: JQuery = null;

    /** The JQuery-wrapped window. */
    #$window: JQuery<Window> = $(window);

    /** The saved height of the comment flag (in pixels). */
    #prevCommentHeight: number = null;

    /** The saved width of the window. */
    #prevWindowWidth: number = null;

    /** Whether the resize event handler is registered. */
    #resizeRegistered = false;

    /**
     * Render the contents of the comment flag.
     *
     * This will display the comment flag and then start listening for
     * events for updating the comment count or repositioning the comment
     * (for zoom level changes and wrapping changes).
     */
    renderContent() {
        this.$el.html(this.template(_.defaults(this.model.attributes, {
            anchorName: this.buildAnchorName(),
        })));

        this.$('.commentflag-count')
            .bindProperty('text', this.model, 'count', {
                elementToModel: false,
            });
    }

    /**
     * Remove the comment from the page.
     *
     * Returns:
     *     TextBasedCommentBlockView:
     *     This object, for chaining.
     */
    remove(): this {
        if (this.#resizeRegistered) {
            this.#$window.off(`resize.${this.cid}`);
        }

        return super.remove();
    }

    /**
     * Set the row span for the comment flag.
     *
     * The comment will update to match the row of lines.
     *
     * Args:
     *     $beginRow (jQuery):
     *         The first row of the comment.
     *
     *     $endRow (jQuery):
     *         The last row of the comment. This may be the same as
     *         ``$beginRow``.
     */
    setRows(
        $beginRow: JQuery,
        $endRow: JQuery,
    ) {
        this.$beginRow = $beginRow;
        this.$endRow = $endRow;

        /*
         * We need to set the sizes and show the element after other layout
         * operations and the DOM have settled.
         */
        _.defer(() => {
            this._updateSize();
            this.$el.show();
        });

        if ($beginRow && $endRow) {
            if (!this.#resizeRegistered) {
                this.#$window.on(`resize.${this.cid}`,
                                 _.bind(this._updateSize, this));
            }
        } else {
            if (this.#resizeRegistered) {
                this.#$window.off(`resize.${this.cid}`);
            }
        }
    }

    /**
     * Position the comment dialog relative to the comment flag position.
     *
     * The dialog will be positioned in the center of the page (horizontally),
     * just to the bottom of the flag.
     *
     * Args:
     *     commentDlg (RB.CommentDialogView):
     *          The view for the comment dialog.
     */
    positionCommentDlg(commentDlg: CommentDialogView) {
        commentDlg.$el.css({
            left: $(document).scrollLeft() +
                  (this.#$window.width() - commentDlg.$el.width()) / 2,
            top: this.$endRow.offset().top + this.$endRow.height(),
        });
    }

    /**
     * Position the comment update notifications bubble.
     *
     * The bubble will be positioned just to the top-right of the flag.
     *
     * Args:
     *     $bubble (jQuery):
     *         The selector for the notification bubble.
     */
    positionNotifyBubble($bubble: JQuery) {
        $bubble.css({
            left: this.$el.width(),
            top: 0,
        });
    }

    /**
     * Return the name for the comment flag anchor.
     *
     * Returns:
     *     string:
     *     The name to use for the anchor element.
     */
    buildAnchorName() {
        return `line${this.model.get('beginLineNum')}`;
    }

    /**
     * Update the size of the comment flag.
     */
    _updateSize() {
        const $endRow = this.$endRow;
        const windowWidth = this.#$window.width();

        if (this.#prevWindowWidth === windowWidth ||
            $endRow.is(':hidden')) {
            /*
             * The view mode that the comment is on is hidden, so bail and
             * try again when its visible. Or the comment size has already
             * been calculated for this window size, so no-op.
             */
            return;
        }

        this.#prevWindowWidth = windowWidth;
        const $el = this.$el;

        /*
         * On IE and Safari, the marginTop in getExtents may be wrong.
         * We force a value that ends up working for us.
         */
        const commentHeight = $endRow.offset().top +
                              $endRow.outerHeight() -
                              this.$beginRow.offset().top -
                              ($el.getExtents('m', 't') || -4);

        if (commentHeight !== this.#prevCommentHeight) {
            $el.height(commentHeight);
            this.#prevCommentHeight = commentHeight;
        }
    }
}
