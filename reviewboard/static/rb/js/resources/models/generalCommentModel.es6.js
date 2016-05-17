/**
 * Provides commenting functionality for review requests, which are not
 * related to any lines of code or files.
 *
 * Examples include suggestions for testing or pointing out errors in
 * the change description. An issue can be opened.
 */
RB.GeneralComment = RB.BaseComment.extend({
    rspNamespace: 'general_comment'
});
