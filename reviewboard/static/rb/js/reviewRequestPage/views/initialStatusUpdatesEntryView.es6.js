/**
 * Displays all the initial status updates.
 *
 * Initial status updates are those which do not correspond to a change
 * description (i.e. those posted against the first revision of a diff or any
 * file attachments that were present when the review request was first
 * published).
 */
RB.ReviewRequestPage.InitialStatusUpdatesEntryView =
    RB.ReviewRequestPage.BaseStatusUpdatesEntryView.extend();
