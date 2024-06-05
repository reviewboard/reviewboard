/**
 * Abstract view for comment blocks.
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';

import {
    EnabledFeatures,
    UserSession,
} from 'reviewboard/common';
import {
    type AbstractCommentBlock,
} from '../models/abstractCommentBlockModel';
import { type CommentDialogView } from './commentDialogView';


/**
 * Abstract view for comment blocks.
 */
@spina
export class AbstractCommentBlockView<
    TModel extends AbstractCommentBlock,
    TElement extends Element = HTMLElement,
    TExtraViewOptions = unknown
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    static events: EventsHash = {
        'click': '_onClicked',
    };

    static modelEvents: EventsHash = {
        'change:draftComment': '_onDraftCommentChanged',
    };

    static tooltipSides = 'lrbt';


    /**********************
     * Instance variables *
     **********************/

    /** The tooltip when hovering over the comment flag. */
    #$tooltip: JQuery;

    /**
     * Dispose the comment block.
     *
     * This will remove the view and the tooltip.
     */
    dispose() {
        this.trigger('removing');
        this.remove();
        this.#$tooltip.remove();
    }

    /**
     * Render the comment block.
     *
     * Along with the block, a floating tooltip will be created that
     * displays summaries of the comments.
     *
     * Returns:
     *     RB.AbstractCommentBlockView:
     *     This object, for chaining.
     */
    render() {
        this.#$tooltip =
            $.tooltip(
                this.$el,
                { side: AbstractCommentBlockView.tooltipSides })
            .attr('data-ink-color-scheme', 'light')
            .addClass('comments');

        this.renderContent();

        this._onDraftCommentChanged();

        this.#updateTooltip();

        return this;
    }

    /**
     * Render the comment content.
     *
     * This should be implemented by subclasses.
     */
    renderContent() {
        // Intentionally left blank.
    }

    /**
     * Hide the tooltip from the page.
     *
     * This will force the tooltip to hide, preventing it from interfering
     * with operations such as moving a comment block.
     *
     * It will automatically show again the next time there is a mouse enter
     * event.
     */
    hideTooltip() {
        this.#$tooltip.hide();
    }

    /**
     * Position the comment dlg to the right side of comment block.
     *
     * This can be overridden to change where the comment dialog will
     * be displayed.
     *
     * Args:
     *     commentDlg (RB.CommentDialogView):
     *          The view for the comment dialog.
     */
    positionCommentDlg(commentDlg: CommentDialogView) {
        commentDlg.positionBeside(this.$el, {
            fitOnScreen: true,
            side: 'r',
        });
    }

    /**
     * Position the notification bubble around the comment block.
     *
     * This can be overridden to change where the bubble will be displayed.
     * By default, it is centered over the block.
     *
     * Args:
     *     $bubble (jQuery):
     *         The selector for the notification bubble.
     */
    positionNotifyBubble($bubble: JQuery) {
        $bubble.move(Math.round((this.$el.width() - $bubble.width()) / 2),
                     Math.round((this.$el.height() - $bubble.height()) / 2));
    }

    /**
     * Notify the user of some update.
     *
     * This notification appears in the comment area.
     *
     * Args:
     *     text (string):
     *         The text to show in the notification.
     *
     *     cb (function, optional):
     *         A callback function to call once the notification has been
     *         removed.
     *
     *     context (object):
     *         Context to bind when calling the ``cb`` callback function.
     */
    notify(
        text: string,
        cb?: (context: object) => void,
        context?: object,
    ) {
        const $bubble = $('<div class="bubble">')
            .css('opacity', 0)
            .appendTo(this.$el)
            .text(text);

        this.positionNotifyBubble($bubble);

        $bubble
            .animate({
                opacity: 0.8,
                top: '-=10px',
            }, 350, 'swing')
            .delay(1200)
            .animate({
                opacity: 0,
                top: '+=10px',
            }, 350, 'swing', () => {
                $bubble.remove();

                if (_.isFunction(cb)) {
                    cb.call(context);
                }
            });
    }

    /**
     * Update the tooltip contents.
     *
     * The contents will show the summary of each comment, including
     * the draft comment, if any.
     */
    #updateTooltip() {
        const $list = $('<ul>');
        const draftComment = this.model.get('draftComment');
        const tooltipTemplate = _.template(dedent`
            <li>
             <div class="reviewer">
              <%- user %>:
             </div>
             <pre class="rich-text"><%= html %></pre>
            </li>
        `);

        if (draftComment) {
            $(tooltipTemplate({
                html: draftComment.get('html'),
                user: UserSession.instance.get('fullName'),
            }))
            .addClass('draft')
            .appendTo($list);
        }

        this.model.get('serializedComments').forEach(comment => {
            $(tooltipTemplate({
                html: comment.html,
                user: comment.user.name,
            }))
            .appendTo($list);
        });

        this.#$tooltip
            .empty()
            .append($list);
    }

    /**
     * Handle changes to the model's draftComment property.
     *
     * If there's a new draft comment, we'll begin listening for updates
     * on it in order to update the tooltip or display notification bubbles.
     *
     * The comment block's style will reflect whether or not we have a
     * draft comment.
     *
     * If the draft comment is deleted, and there are no other comments,
     * the view will be removed.
     */
    private _onDraftCommentChanged() {
        const comment = this.model.get('draftComment');

        if (!comment) {
            this.$el.removeClass('draft');

            return;
        }

        comment.on('change:text', this.#updateTooltip, this);

        comment.on('destroy', () => {
            this.notify(gettext('Comment Deleted'), () => {
                // Discard the comment block if empty.
                if (this.model.isEmpty()) {
                    this.$el.fadeOut(350, () => this.dispose());
                } else {
                    this.$el.removeClass('draft');
                    this.#updateTooltip();
                }
            });
        });

        comment.on('saved', options => {
            this.#updateTooltip();

            if (!options.boundsUpdated) {
                this.notify(gettext('Comment Saved'));
            }

            if (!EnabledFeatures.unifiedBanner) {
                RB.DraftReviewBannerView.instance.show();
            }
        });

        this.$el.addClass('draft');
    }

    /**
     * Handle the comment block being clicked.
     *
     * Emits the 'clicked' signal so that parent views can process it.
     */
    protected _onClicked() {
        this.trigger('clicked');
    }
}
