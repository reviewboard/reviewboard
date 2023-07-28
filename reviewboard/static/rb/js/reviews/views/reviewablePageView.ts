/**
 * A page managing reviewable content for a review request.
 */
import { BaseView, EventsHash, spina } from '@beanbag/spina';

import {
    EnabledFeatures,
    PageView,
    UserSession,
} from 'reviewboard/common';
import { PageViewOptions } from 'reviewboard/common/views/pageView';
import { DnDUploader } from 'reviewboard/ui';

import { ReviewRequestEditor } from '../models/reviewRequestEditorModel';
import { ReviewablePage } from '../models/reviewablePageModel';
import { UnifiedBanner } from '../models/unifiedBannerModel';
import { ReviewDialogView } from './reviewDialogView';
import { ReviewRequestEditorView } from './reviewRequestEditorView';
import { UnifiedBannerView } from './unifiedBannerView';


/**
 * Update information as received from the server.
 */
interface UpdateInfo {
    /** The summary of the update. */
    summary: string;

    /** Information about the user who made the update. */
    user: {
        fullname?: string,
        url: string,
        username: string,
    };
}


/**
 * Options for the UpdatesBubbleView.
 */
interface UpdatesBubbleViewOptions {
    /** Information about the update, fetched from the server. */
    updateInfo: UpdateInfo;
}


/**
 * An update bubble showing an update to the review request or a review.
 */
@spina
class UpdatesBubbleView extends BaseView<
    undefined,
    HTMLDivElement,
    UpdatesBubbleViewOptions
> {
    static id = 'updates-bubble';

    static template = _.template([
        '<span id="updates-bubble-summary"><%- summary %></span>',
        ' by ',
        '<a href="<%- user.url %>" id="updates-bubble-user">',
        '<%- user.fullname || user.username %>',
        '</a>',
        '<span id="updates-bubble-buttons">',
        ' <a href="#" class="update-page"><%- updatePageText %></a>',
        ' | ',
        ' <a href="#" class="ignore"><%- ignoreText %></a>',
    ].join(''));

    static events: EventsHash = {
        'click .ignore': '_onIgnoreClicked',
        'click .update-page': '_onUpdatePageClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    /** Options for the view. */
    options: UpdatesBubbleViewOptions;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (UpdatesBubbleViewOptions):
     *         Options for the view.
     */
    initialize(options: UpdatesBubbleViewOptions) {
        this.options = options;
    }

    /**
     * Render the bubble with the information provided during construction.
     *
     * The bubble starts hidden. The caller must call open() to display it.
     */
    onInitialRender() {
        this.$el
            .html(UpdatesBubbleView.template(_.defaults({
                ignoreText: _`Ignore`,
                updatePageText: _`Update Page`,
            }, this.options.updateInfo)))
            .hide();
    }

    /**
     * Open the bubble on the screen.
     */
    open() {
        this.$el
            .css('position', 'fixed')
            .fadeIn();
    }

    /**
     * Close the update bubble.
     *
     * After closing, the bubble will be removed from the DOM.
     */
    close() {
        this.trigger('closed');
        this.$el.fadeOut(_.bind(this.remove, this));
    }

    /**
     * Handle clicks on the "Update Page" link.
     *
     * Loads the review request page.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event which triggered the action.
     */
    _onUpdatePageClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('updatePage');
    }

    /*
     * Handle clicks on the "Ignore" link.
     *
     * Ignores the update and closes the page.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event which triggered the action.
     */
    _onIgnoreClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        this.close();
    }
}


/**
 * Options for the ReviewablePageView.
 */
export interface ReviewablePageViewOptions extends PageViewOptions {
    /** The model attributes for a new RB.ReviewRequest instance. */
    reviewRequestData?: object; // TODO: update once ReviewRequest is TS

    /** The model attributes for a new ReviewRequestEditor instance. */
    editorData?: Partial<ReviewRequestEditorAttrs>;

    /** The last known timestamp for activity on this review request. */
    lastActivityTimestamp?: string;

    /** The type of updates to check for. */
    checkUpdatesType?: string;
}


/**
 * A page managing reviewable content for a review request.
 *
 * This provides common functionality for any page associated with a review
 * request, such as the diff viewer, review UI, or the review request page
 * itself.
 */
@spina({
    prototypeAttrs: ['events'],
})
export class ReviewablePageView<
    TModel extends ReviewablePage = ReviewablePage,
    TElement extends HTMLDivElement = HTMLDivElement,
    TExtraViewOptions extends ReviewablePageViewOptions =
        ReviewablePageViewOptions
> extends PageView<TModel, TElement, TExtraViewOptions> {
    static events: EventsHash = {
        'click #action-legacy-edit-review': '_onEditReviewClicked',
        'click #action-legacy-add-general-comment': 'addGeneralComment',
        'click #action-legacy-ship-it': 'shipIt',
        'click .rb-o-mobile-menu-label': '_onMenuClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The review request editor. */
    reviewRequestEditorView: ReviewRequestEditorView;

    /** The draft review banner, if present. */
    draftReviewBanner: RB.DraftReviewBannerview;

    /** The unified banner, if present. */
    unifiedBanner: UnifiedBannerView = null;

    /** The star manager. */
    #starManager: RB.StarManagerView;

    /** The URL to the default favicon. */
    #favIconURL: string = null;

    /** The URL to the favicon showing an active notification. */
    #favIconNotifyURL: string = null;

    /** The URL to the logo image to use for notifications. */
    #logoNotificationsURL: string = null;

    /** The updates bubble view. */
    _updatesBubble: UpdatesBubbleView = null;

    /**
     * Initialize the page.
     *
     * This will construct a ReviewRequest, CommentIssueManager,
     * ReviewRequestEditor, and other required objects, based on data
     * provided during construction.
     *
     * Args:
     *     options (ReviewablePageViewOptions):
     *         Options for the view.
     */
    initialize(options: ReviewablePageViewOptions) {
        super.initialize(options);

        this.options = options;

        DnDUploader.create();

        this.reviewRequestEditorView = new ReviewRequestEditorView({
            el: $('#review-request'),
            model: this.model.reviewRequestEditor,
        });

        /*
         * Some extensions, like Power Pack and rbstopwatch, expect a few
         * legacy attributes on the view. Set these here so these extensions
         * can access them. Note that extensions should ideally use the new
         * form, if they're able to support Review Board 3.0+.
         */
        ['reviewRequest', 'pendingReview'].forEach(attrName => {
            this[attrName] = this.model.get(attrName);

            this.listenTo(this.model, `change:${attrName}`, () => {
                this[attrName] = this.model.get(attrName);
            });
        });

        /*
         * Allow the browser to report notifications, if the user has this
         * enabled.
         */
        RB.NotificationManager.instance.setup();

        if (UserSession.instance.get('authenticated')) {
            this.#starManager = new RB.StarManagerView({
                el: this.$('.star').parent(),
                model: new RB.StarManager(),
            });
        }

        this.listenTo(this.model, 'reviewRequestUpdated',
                      this._onReviewRequestUpdated);
    }

    /**
     * Render the page.
     */
    renderPage() {
        const $favicon = $('head').find('link[rel="shortcut icon"]');

        this.#favIconURL = $favicon.attr('href');
        this.#favIconNotifyURL = STATIC_URLS['rb/images/favicon_notify.ico'];
        this.#logoNotificationsURL = STATIC_URLS['rb/images/logo.png'];

        const pendingReview = this.model.get('pendingReview');
        const reviewRequest = this.model.get('reviewRequest');

        if (EnabledFeatures.unifiedBanner) {
            if (UserSession.instance.get('authenticated')) {
                this.unifiedBanner = new UnifiedBannerView({
                    el: $('#unified-banner'),
                    model: new UnifiedBanner({
                        pendingReview: pendingReview,
                        reviewRequest: reviewRequest,
                        reviewRequestEditor: this.model.reviewRequestEditor,
                    }),
                    reviewRequestEditorView: this.reviewRequestEditorView,
                });
                this.unifiedBanner.render();
            }
        } else {
            this.draftReviewBanner = RB.DraftReviewBannerView.create({
                el: $('#review-banner'),
                model: pendingReview,
                reviewRequestEditor: this.model.reviewRequestEditor,
            });

            this.listenTo(pendingReview, 'destroy published',
                          () => this.draftReviewBanner.hideAndReload());
        }

        this.reviewRequestEditorView.render();
    }

    /**
     * Remove this view from the page.
     *
     * Returns:
     *     ReviewablePageView:
     *     This object, for chaining.
     */
    remove(): this {
        if (this.draftReviewBanner) {
            this.draftReviewBanner.remove();
        }

        if (this.unifiedBanner) {
            this.unifiedBanner.remove();
        }

        return super.remove();
    }

    /**
     * Return data to use for assessing cross-tab page reloads.
     *
     * This returns a filter blob that will be recognized by all other tabs
     * that have the same review request.
     *
     * Version Added:
     *     6.0
     */
    getReloadData(): unknown {
        return {
            'review-request': this.model.get('reviewRequest').id,
        };
    }

    /**
     * Return the review request editor view.
     *
     * Returns:
     *     ReviewRequestEditorView:
     *     The review request editor view.
     */
    getReviewRequestEditorView(): ReviewRequestEditorView {
        return this.reviewRequestEditorView;
    }

    /**
     * Return the review request editor model.
     *
     * Returns:
     *     ReviewRequestEditor:
     *     The review request editor model.
     */
    getReviewRequestEditorModel(): ReviewRequestEditor {
        return this.model.reviewRequestEditor;
    }

    /**
     * Catch the review updated event and send the user a visual update.
     *
     * This function will handle the review updated event and decide whether
     * to send a notification depending on browser and user settings.
     *
     * Args:
     *     info (UpdateInfo):
     *         The last update information for the request.
     */
    _onReviewRequestUpdated(info: UpdateInfo) {
        this.#updateFavIcon(this.#favIconNotifyURL);

        if (RB.NotificationManager.instance.shouldNotify()) {
            this._showDesktopNotification(info);
        }

        this._showUpdatesBubble(info);
    }

    /**
     * Create the updates bubble showing information about the last update.
     *
     * Args:
     *     info (UpdateInfo):
     *         The last update information for the request.
     */
    _showUpdatesBubble(info: UpdateInfo) {
        if (this._updatesBubble) {
            this._updatesBubble.remove();
        }

        const reviewRequest = this.model.get('reviewRequest');

        this._updatesBubble = new UpdatesBubbleView({
            updateInfo: info,
        });

        this.listenTo(this._updatesBubble, 'closed',
                      () => this.#updateFavIcon(this.#favIconURL));

        this.listenTo(this._updatesBubble, 'updatePage', () => {
            RB.navigateTo(reviewRequest.get('reviewURL'));
        });

        this._updatesBubble.render().$el.appendTo(this.$el);
        this._updatesBubble.open();
    }

    /**
     * Show the user a desktop notification for the last update.
     *
     * This function will create a notification if the user has not
     * disabled desktop notifications and the browser supports HTML5
     * notifications.
     *
     *  Args:
     *     info (UpdateInfo):
     *         The last update information for the request.
     */
    _showDesktopNotification(info: UpdateInfo) {
        const reviewRequest = this.model.get('reviewRequest');
        const name = info.user.fullname || info.user.username;

        RB.NotificationManager.instance.notify({
            body: _`Review request #${reviewRequest.id}, by ${name}`,
            iconURL: this.#logoNotificationsURL,
            onClick: () => {
                RB.navigateTo(reviewRequest.get('reviewURL'));
            },
            title: info.summary,
        });
    }

    /**
     * Update the favicon for the page.
     *
     * This is used to change the favicon shown on the page based on whether
     * there's a server-side update notification for the review request.
     *
     * Args:
     *     url (string):
     *         The URL to use for the shortcut icon.
     */
    #updateFavIcon(url: string) {
        $('head')
            .find('link[rel="shortcut icon"]')
                .remove()
            .end()
            .append($('<link/>')
                .attr({
                    href: url,
                    rel: 'shortcut icon',
                    type: 'image/x-icon',
                }));
    }

    /**
     * Handle a click on the "Edit Review" button.
     *
     * Displays a review dialog.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event which triggered the action.
     */
    _onEditReviewClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        ReviewDialogView.create({
            review: this.model.get('pendingReview'),
            reviewRequestEditor: this.model.reviewRequestEditor,
        });

        return false;
    }

    /**
     * Add a new general comment.
     *
     * Args:
     *     e (JQuery.ClickEvent, optional):
     *         The event which triggered the action.
     */
    addGeneralComment(e?: JQuery.ClickEvent) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        const pendingReview = this.model.get('pendingReview');
        const comment = pendingReview.createGeneralComment(
            undefined,
            UserSession.instance.get('commentsOpenAnIssue'));

        if (!EnabledFeatures.unifiedBanner) {
            this.listenTo(comment, 'saved',
                          () => RB.DraftReviewBannerView.instance.show());
        }

        RB.CommentDialogView.create({
            comment: comment,
            reviewRequestEditor: this.model.reviewRequestEditor,
        });

        return false;
    }

    /**
     * Handle a click on the "Ship It" button.
     *
     * Confirms that the user wants to post the review, and then posts it
     * and reloads the page.
     *
     * Args:
     *     e (JQuery.ClickEvent, optional):
     *         The event which triggered the action, if available.
     */
    async shipIt(e?: JQuery.ClickEvent) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        if (confirm(_`Are you sure you want to post this review?`)) {
            await this.model.markShipIt();

            const reviewRequest = this.model.get('reviewRequest');
            RB.navigateTo(reviewRequest.get('reviewURL'));
        }

        return false;
    }

    /**
     * Generic handler for menu clicks.
     *
     * This simply prevents the click from bubbling up or invoking the
     * default action. This function is used for dropdown menu titles
     * so that their links do not send a request to the server when one
     * of their dropdown actions are clicked.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event which triggered the action.
     */
    _onMenuClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        const $menuButton = $(e.currentTarget).find('a');

        const expanded = $menuButton.attr('aria-expanded');
        const target = $menuButton.attr('aria-controls');
        const $target = this.$(`#${target}`);

        if (expanded === 'false') {
            $menuButton.attr('aria-expanded', 'true');
            $target.addClass('-is-visible');
        } else {
            $menuButton.attr('aria-expanded', 'false');
            $target.removeClass('-is-visible');
        }
    }
}
