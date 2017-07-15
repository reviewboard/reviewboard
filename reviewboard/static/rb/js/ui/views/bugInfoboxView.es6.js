/**
 * An infobox for displaying information on bug reports.
 */
RB.BugInfoboxView = RB.BaseInfoboxView.extend({
    infoboxID: 'bug-infobox',
});


$.fn.bug_infobox = RB.InfoboxManagerView.createJQueryFn(RB.BugInfoboxView);
