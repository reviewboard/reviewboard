/**
 * View for managing the issue status of a comment.
 */

import {
    type BaseComponentViewOptions,
    BaseComponentView,
    paint,
    renderInto,
} from '@beanbag/ink';
import {
    type BaseModel,
    type EventsHash,
    spina,
} from '@beanbag/spina';

import {
    type BaseComment,
    CommentIssueStatusType,
    UserSession,
} from 'reviewboard/common';
import {
    type CommentIssueManager,
    type CommentIssueManagerCommentType,
    type IssueStatusUpdatedEventData,
} from '../models/commentIssueManagerModel';


/**
 * Options for CommentIssueBarView.
 *
 * Version Added:
 *     7.0
 */
export interface CommentIssueBarViewOptions extends BaseComponentViewOptions {
    /** Whether the user has permission to verify issues that require it. */
    canVerify: boolean;

    /** The ID of the comment object. */
    commentID: number;

    /** The type of comment being modified. */
    commentType: CommentIssueManagerCommentType;

    /** Whether the issue bar is interactive. */
    interactive: boolean;

    /** The currently-set issue status. */
    issueStatus: CommentIssueStatusType;

    /** The ID of the reivew that the comment is filed on. */
    reviewID: number;

    /**
     * The issue manager for accessing and setting issue statuses.
     *
     * If not provided, the current one for the page will be used.
     */
    commentIssueManager?: CommentIssueManager;
}


/**
 * Manages a comment's issue status bar.
 *
 * The buttons on the bar will update the comment's issue status on the server
 * when clicked. The bar will update to reflect the issue status of any
 * comments tracked by the issue summary table.
 *
 * Version Changed:
 *     7.0:
 *     Rewritten for the new ``.rb-c-issue-bar`` component, for improved
 *     accessibility, and for use in Ink's craft/paint mechanism.
 */
@spina
export class CommentIssueBarView<
    TOptions extends CommentIssueBarViewOptions = CommentIssueBarViewOptions,
> extends BaseComponentView<
    BaseModel,
    HTMLDivElement,
    TOptions
> {
    static className = 'rb-c-issue-bar';

    static events: EventsHash = {
        'click .ink-c-button[data-action="drop"]': '_onDropClicked',
        'click .ink-c-button[data-action="reopen"]': '_onReopenClicked',
        'click .ink-c-button[data-action="resolve"]': '_onFixedClicked',
        'click .ink-c-button[data-action="verify-dropped"]':
            '_onVerifyDroppedClicked',
        'click .ink-c-button[data-action="verify-resolved"]':
            '_onVerifyResolvedClicked',
    };

    /** The actions available on the issue bar. */
    static Actions = {
        'drop': {
            label: _`Drop`,
            onClick: '_onDropClicked',
        },
        'reopen': {
            label: _`Re-open`,
            onClick: '_onReopenClicked',
        },
        'resolve': {
            label: _`Fixed`,
            onClick: '_onFixedClicked',
        },
        'verify-dropped': {
            label: _`Verify Dropped`,
            onClick: '_onVerifyDroppedClicked',
            requireCanVerify: true,
        },
        'verify-resolved': {
            label: _`Verify Fixed`,
            onClick: '_onVerifyFixedClicked',
            requireCanVerify: true,
        },
    };

    /**
     * Information on each valid status.
     */
    static StatusInfo = {
        [CommentIssueStatusType.DROPPED]: {
            actions: ['reopen'],
            message: _`The issue has been dropped.`,
        },
        [CommentIssueStatusType.OPEN]: {
            actions: ['resolve', 'drop'],
            message: _`An issue was opened.`,
        },
        [CommentIssueStatusType.RESOLVED]: {
            actions: ['reopen'],
            message: _`The issue has been resolved.`,
        },
        [CommentIssueStatusType.VERIFYING_DROPPED]: {
            actions: ['reopen', 'verify-dropped'],
            message: _`Waiting for verification before dropping...`,
        },
        [CommentIssueStatusType.VERIFYING_RESOLVED]: {
            actions: ['reopen', 'verify-resolved'],
            message: _`Waiting for verification before resolving...`,
        },
    };

    /**********************
     * Instance variables *
     **********************/

    /*
     * Comment/issue management state.
     */

    /** The ID of the comment object. */
    #commentID: number;

    /** The type of comment being modified. */
    #commentType: CommentIssueManagerCommentType;

    /** The issue manager for accessing and setting issue statuses. */
    #issueManager: CommentIssueManager;

    /** The ID of the reivew that the comment is filed on. */
    #reviewID: number;

    /*
     * Access control state.
     */

    /** Whether the user has permission to verify issues that require it. */
    #canVerify: boolean;

    /** Whether the issue bar is interactive. */
    #interactive: boolean;

    /*
     * HTML elements.
     */

    /** The element for the actions area. */
    #actionsEl: HTMLElement = null;

    /** The element for the issue status message text. */
    #messageEl: HTMLElement = null;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (CommentBarIssueViewOptions):
     *         Options for the view.
     */
    initialize(options: TOptions) {
        super.initialize(options);

        console.assert(
            options.commentID,
            'commentID must be provided to CommentIssueBarView.');
        console.assert(
            options.commentType,
            'commentType must be provided to CommentIssueBarView.');
        console.assert(
            options.issueStatus,
            'issueStatus must be provided to CommentIssueBarView.');
        console.assert(
            options.reviewID,
            'reviewID must be provided to CommentIssueBarView.');

        this.#commentID = options.commentID;
        this.#commentType = options.commentType;
        this.#reviewID = options.reviewID;

        this.#interactive = !!options.interactive;
        this.#canVerify = !!options.canVerify;

        this.#issueManager =
            options.commentIssueManager ||
            RB.PageManager.getPage().model.commentIssueManager;
    }

    /**
     * Handle initial rendering of the view.
     *
     * If this view is managing an existing HTML structure, state from that
     * structure will be loaded. Otherwise it will construct the structure.
     *
     * The action buttons and message will be updated whenever the issue
     * status changes.
     */
    protected onComponentInitialRender() {
        const options = this.initialComponentState.options;
        const el = this.el;

        if (el.children.length === 0) {
            if (!el.id) {
                el.id = `issue-bar-${options.commentID}`;
            }

            const labelID = `${el.id}__label`;
            el.setAttribute('aria-labelledby', labelID);

            /* This is a brand-new instance of the bar. */
            this.#actionsEl = paint<HTMLElement>`
                <span class="rb-c-issue-bar__actions"/>
            `;

            this.#messageEl = paint<HTMLElement>`
                <label class="rb-c-issue-bar__message"
                       id="${labelID}"/>
            `;

            /* Update the actions before we add to the DOM. */
            this.#updateIssueBar(options.issueStatus);

            renderInto(el, paint`
                <span class="rb-c-issue-bar__icon" aria-hidden="true"/>
                ${this.#messageEl}
                ${this.#actionsEl}
                <a class="rb-c-issue-bar__all-issues-link"
                   href="#issue-summary">
                 ${_`Show all issues`}
                </a>
            `);
        } else {
            this.#actionsEl = el.querySelector('.rb-c-issue-bar__actions');
            this.#messageEl = el.querySelector('.rb-c-issue-bar__message');

            console.assert(this.#actionsEl,
                           'Missing rb-c-issue-bar__actions element');
            console.assert(this.#messageEl,
                           'Missing rb-c-issue-bar__message element');

            this.#updateIssueBar(options.issueStatus);
        }

        const issueManager = this.#issueManager;

        this.listenTo(
            this.#issueManager,
            `issueStatusUpdated:${this.#commentType}:${this.#commentID}`,
            this.#onIssueStatusUpdated);
    }

    /**
     * Return whether the current user can verify a given comment.
     *
     * This will check if the comment needs verification and whether the
     * current user is the one who filed the comment.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment to check.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the issue needs verification and can be verified.
     *     ``false`` if it cannot.
     */
    #canVerifyComment(
        comment: BaseComment,
    ): boolean {
        return this.#interactive &&
               comment.requiresVerification() &&
               comment.getAuthorUsername() !==
                   UserSession.instance.get('username');
    }

    /**
     * Set the issue status of the comment on the server.
     *
     * Args:
     *     newIssueStatus (CommentIssueStatusType):
     *         The new issue status.
     *
     *     clickedAction (string):
     *         The action that invoked this status update.
     *
     *         This is used to set the right states on the action buttons.
     */
    #setStatus(
        newIssueStatus: CommentIssueStatusType,
        clickedAction: string,
    ) {
        const buttonEls = this.#actionsEl
            .querySelectorAll<HTMLButtonElement>('.ink-c-button');

        for (const buttonEl of buttonEls) {
            if (buttonEl.dataset.action === clickedAction) {
                buttonEl.setAttribute('aria-busy', 'true');
            } else {
                buttonEl.disabled = true;
            }
        }

        this.#issueManager.setCommentIssueStatus({
            commentID: this.#commentID,
            commentType: this.#commentType,
            newIssueStatus: newIssueStatus,
            reviewID: this.#reviewID,
        });
    }

    /**
     * Update the issue bar's actions and message based on the current state.
     *
     * This will rebuild the list of buttons for the new issue status, and
     * update the message and attributes.
     *
     * Args:
     *     issueStatus (CommentIssueStatusType):
     *         The issue status type to reflect.
     */
    #updateIssueBar(issueStatus: CommentIssueStatusType) {
        const el = this.el;
        const actionsInfo = CommentIssueBarView.Actions;
        const statusInfo = CommentIssueBarView.StatusInfo[issueStatus];

        el.dataset.issueStatus = issueStatus;
        this.#messageEl.textContent = statusInfo.message;

        const actionEls: HTMLElement[] = [];

        if (this.#interactive) {
            for (const action of statusInfo.actions) {
                const actionInfo = actionsInfo[action];
                console.assert(actionInfo,
                               'Invalid CommentIssueBarView action %s.',
                               action);

                if (!actionInfo.requireCanVerify || this.#canVerify) {
                    actionEls.push(paint`
                        <Ink.Button data-action="${action}">
                         ${actionInfo.label}
                        </Ink.Button>
                    `);
                }
            }
        }

        renderInto(this.#actionsEl, actionEls, {
            empty: true,
        });
    }

    /**
     * Handle a change to an issue status.
     *
     * Args:
     *     eventData (object):
     *         Data from the event.
     */
    #onIssueStatusUpdated(eventData: IssueStatusUpdatedEventData) {
        this.#updateIssueBar(eventData.newIssueStatus);
        this.trigger('statusChanged',
                     eventData.oldIssueStatus,
                     eventData.newIssueStatus);
    }

    /**
     * Handler for when "Drop" is clicked.
     *
     * Marks the issue as dropped.
     */
    async _onDropClicked() {
        const comment = this.#issueManager.getOrCreateComment({
            commentID: this.#commentID,
            commentType: this.#commentType,
            reviewID: this.#reviewID,
        });

        await comment.ready();

        this.#setStatus(
            (this.#canVerifyComment(comment)
             ? CommentIssueStatusType.VERIFYING_DROPPED
             : CommentIssueStatusType.DROPPED),
            'drop');
    }

    /**
     * Handler for when "Re-open" is clicked.
     *
     * Reopens the issue.
     */
    _onReopenClicked() {
        this.#setStatus(CommentIssueStatusType.OPEN, 'reopen');
    }

    /**
     * Handler for when "Fixed" is clicked.
     *
     * Marks the issue as fixed.
     */
    async _onFixedClicked() {
        const comment = this.#issueManager.getOrCreateComment({
            commentID: this.#commentID,
            commentType: this.#commentType,
            reviewID: this.#reviewID,
        });

        await comment.ready();

        this.#setStatus(
            (this.#canVerifyComment(comment)
             ? CommentIssueStatusType.VERIFYING_RESOLVED
             : CommentIssueStatusType.RESOLVED),
            'resolve');
    }

    /**
     * Handler for when "Verify Dropped" is clicked.
     */
    _onVerifyDroppedClicked() {
        this.#setStatus(CommentIssueStatusType.DROPPED, 'verify-dropped');
    }

    /**
     * Handler for when "Verify Fixed" is clicked.
     */
    _onVerifyResolvedClicked() {
        this.#setStatus(CommentIssueStatusType.RESOLVED, 'verify-resolved');
    }
}
