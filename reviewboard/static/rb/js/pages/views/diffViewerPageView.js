/*
 * Manages the diff viewer page.
 *
 * This provides functionality for the diff viewer page for managing the
 * loading and display of diffs.
 */
RB.DiffViewerPageView = RB.ReviewablePageView.extend({
    /*
     * Queues loading of a diff.
     *
     * When the diff is loaded, it will be placed into the appropriate location
     * in the diff viewer. The anchors on the page will be rebuilt. This will
     * then trigger the loading of the next file.
     */
    queueLoadDiff: function(reviewRequestURL, fileDiffID, fileDiffRevision,
                            interFileDiffID, interFileDiffRevision,
                            fileIndex, serializedComments) {
        RB.loadFileDiff(reviewRequestURL, fileDiffID, fileDiffRevision,
                        interFileDiffID, interFileDiffRevision, fileIndex,
                        serializedComments);
    }
});
