PIPELINE_JAVASCRIPT = {
    '3rdparty-base': {
        'source_filenames': (
            'lib/js/3rdparty-base/index.ts',
        ),
        'output_filename': 'lib/js/3rdparty-base.min.js',
    },
    '3rdparty': {
        'source_filenames': (
            'lib/js/3rdparty/index.ts',
        ),
        'output_filename': 'lib/js/3rdparty.min.js',
    },
    '3rdparty-jsonlint': {
        'source_filenames': (
            'lib/js/jsonlint/index.ts',
        ),
        'output_filename': 'lib/js/3rdparty-jsonlint.min.js',
    },
    'js-test-libs': {
        'source_filenames': (
            # The order matters for the Jasmine modules.
            'lib/js/js-test-libs/jasmine-5.1.0.js',
            'lib/js/js-test-libs/jasmine-html-5.1.0.js',
            'lib/js/js-test-libs/jasmine-boot0-5.1.0.js',
            'lib/js/js-test-libs/jasmine-boot1-5.1.0.js',
            'lib/js/js-test-libs/jasmine.hide-filtered-1.0.js',
            'lib/js/js-test-libs/jasmine.sourcemaps-1.0.js',
            'lib/js/js-test-libs/sourcemapped-stacktrace.js',
            'lib/js/js-test-libs/index.ts',
        ),
        'output_filename': 'rb/js/js-test-libs.min.js',
    },
    'js-tests': {
        'source_filenames': (
            'rb/js/tests/index.ts',
            'rb/js/admin/tests/relatedGroupSelectorViewTests.es6.js',
            'rb/js/admin/tests/relatedRepoSelectorViewTests.es6.js',
            'rb/js/admin/tests/relatedUserSelectorViewTests.es6.js',
            'rb/js/admin/models/tests/dashboardPageModelTests.es6.js',
            'rb/js/admin/models/tests/inlineFormGroupModelTests.es6.js',
            'rb/js/admin/models/tests/newsWidgetModelTests.es6.js',
            'rb/js/admin/views/tests/dashboardPageViewTests.es6.js',
            'rb/js/admin/views/tests/newsWidgetViewTests.es6.js',
            'rb/js/admin/views/tests/inlineFormGroupViewTests.es6.js',
            'rb/js/admin/views/tests/inlineFormViewTests.es6.js',
            'rb/js/collections/tests/filteredCollectionTests.es6.js',
            'rb/js/configForms/models/tests/resourceListItemModelTests.es6.js',
            'rb/js/diffviewer/models/tests/diffCommitModelTests.es6.js',
            'rb/js/diffviewer/models/tests/diffRevisionModelTests.es6.js',
            'rb/js/diffviewer/models/tests/paginationModelTests.es6.js',
            'rb/js/diffviewer/views/tests/diffCommitListViewTests.es6.js',
            'rb/js/models/tests/uploadDiffModelTests.es6.js',
            'rb/js/newReviewRequest/views/tests/branchesViewTests.es6.js',
            'rb/js/newReviewRequest/views/tests/postCommitViewTests.es6.js',
            'rb/js/newReviewRequest/views/tests/repositorySelectionViewTests.es6.js',
            'rb/js/pages/models/tests/pageManagerModelTests.es6.js',
            'rb/js/resources/collections/tests/repositoryBranchesCollectionTests.es6.js',
            'rb/js/resources/collections/tests/repositoryCommitsCollectionTests.es6.js',
            'rb/js/resources/models/tests/baseCommentReplyModelTests.es6.js',
            'rb/js/resources/models/tests/diffCommentModelTests.es6.js',
            'rb/js/resources/models/tests/draftReviewRequestModelTests.es6.js',
            'rb/js/resources/models/tests/fileAttachmentCommentModelTests.es6.js',
            'rb/js/resources/models/tests/fileDiffModelTests.es6.js',
            'rb/js/resources/models/tests/generalCommentModelTests.es6.js',
            'rb/js/resources/models/tests/screenshotModelTests.es6.js',
            'rb/js/resources/models/tests/screenshotCommentModelTests.es6.js',
            'rb/js/resources/models/tests/repositoryBranchModelTests.es6.js',
            'rb/js/resources/models/tests/repositoryCommitModelTests.es6.js',
            'rb/js/resources/models/tests/userFileAttachmentModelTests.es6.js',
            'rb/js/resources/models/tests/validateDiffModelTests.es6.js',
            'rb/js/reviewRequestPage/models/tests/changeEntryModelTests.es6.js',
            'rb/js/reviewRequestPage/models/tests/entryModelTests.es6.js',
            'rb/js/reviewRequestPage/models/tests/reviewEntryModelTests.es6.js',
            'rb/js/reviewRequestPage/models/tests/reviewReplyEditorModelTests.es6.js',
            'rb/js/reviewRequestPage/models/tests/reviewRequestPageModelTests.es6.js',
            'rb/js/reviewRequestPage/models/tests/statusUpdatesEntryModelTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/baseStatusUpdatesEntryViewTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/issueSummaryTableViewTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/reviewEntryViewTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/reviewReplyDraftBannerViewTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/reviewReplyEditorViewTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/reviewRequestPageViewTests.es6.js',
            'rb/js/reviewRequestPage/views/tests/reviewViewTests.es6.js',
            'rb/js/ui/views/tests/dialogViewTests.es6.js',
            'rb/js/ui/views/tests/drawerViewTests.es6.js',
            'rb/js/ui/views/tests/formViewTests.es6.js',
            'rb/js/ui/views/tests/infoboxManagerViewTests.es6.js',
            'rb/js/ui/views/tests/menuButtonViewTests.es6.js',
            'rb/js/ui/views/tests/menuViewTests.es6.js',
            'rb/js/ui/views/tests/notificationManagerTests.es6.js',
            'rb/js/ui/views/tests/scrollManagerViewTests.es6.js',
            'rb/js/utils/tests/apiUtilsTests.es6.js',
            'rb/js/utils/tests/dataUtilsTests.es6.js',
            'rb/js/utils/tests/keyBindingUtilsTests.es6.js',
            'rb/js/utils/tests/linkifyUtilsTests.es6.js',
            'rb/js/utils/tests/urlUtilsTests.es6.js',
            'rb/js/views/tests/clientLoginViewTests.es6.js',
            'rb/js/views/tests/collectionViewTests.es6.js',
            'rb/js/views/tests/diffFragmentQueueViewTests.es6.js',
            'rb/js/views/tests/diffFragmentViewTests.es6.js',
            'rb/js/views/tests/draftReviewBannerViewTests.es6.js',
            'rb/js/views/tests/screenshotThumbnailViewTests.es6.js',
            'rb/js/views/tests/uploadAttachmentViewTests.es6.js',
        ),
        'output_filename': 'rb/js/js-tests.min.js',
    },
    'common': {
        'source_filenames': (
            # Include the common ESM bundle and the extensions bundle. This
            # will ensure they're both exposed as "RB", but allow
            # `reviewboard/extensions` to be a separate ESM bundle that
            # extension code can target.
            'rb/js/common/index.ts',
            'rb/js/extensions/index.ts',

            # Legacy JavaScript
            'rb/js/utils/underscoreUtils.es6.js',
            'rb/js/init.es6.js',
            'rb/js/utils/apiErrors.es6.js',
            'rb/js/utils/apiUtils.es6.js',
            'rb/js/utils/dataUtils.es6.js',
            'rb/js/utils/linkifyUtils.es6.js',
            'rb/js/utils/mathUtils.es6.js',
            'rb/js/utils/keyBindingUtils.es6.js',
            'rb/js/utils/urlUtils.es6.js',
            'rb/js/collections/filteredCollection.es6.js',
            'rb/js/pages/models/pageManagerModel.es6.js',
            'rb/js/resources/models/apiTokenModel.es6.js',
            'rb/js/resources/models/repositoryBranchModel.es6.js',
            'rb/js/resources/models/repositoryCommitModel.es6.js',
            'rb/js/resources/models/draftReviewRequestModel.es6.js',
            'rb/js/resources/models/baseCommentReplyModel.es6.js',
            'rb/js/resources/models/diffCommentModel.es6.js',
            'rb/js/resources/models/diffCommentReplyModel.es6.js',
            'rb/js/resources/models/diffModel.es6.js',
            'rb/js/resources/models/fileAttachmentCommentModel.es6.js',
            'rb/js/resources/models/fileAttachmentCommentReplyModel.es6.js',
            'rb/js/resources/models/generalCommentModel.es6.js',
            'rb/js/resources/models/generalCommentReplyModel.es6.js',
            'rb/js/resources/models/fileDiffModel.es6.js',
            'rb/js/resources/models/screenshotModel.es6.js',
            'rb/js/resources/models/screenshotCommentModel.es6.js',
            'rb/js/resources/models/screenshotCommentReplyModel.es6.js',
            'rb/js/resources/models/userFileAttachmentModel.es6.js',
            'rb/js/resources/models/validateDiffModel.es6.js',
            'rb/js/resources/collections/repositoryBranchesCollection.es6.js',
            'rb/js/resources/collections/repositoryCommitsCollection.es6.js',
            'rb/js/ui/views/dialogView.es6.js',
            'rb/js/ui/views/formView.es6.js',
            'rb/js/ui/views/baseInfoboxView.es6.js',
            'rb/js/ui/views/infoboxManagerView.es6.js',
            'rb/js/ui/views/bugInfoboxView.es6.js',
            'rb/js/ui/views/drawerView.es6.js',
            'rb/js/ui/views/notificationManager.es6.js',
            'rb/js/ui/views/reviewRequestInfoboxView.es6.js',
            'rb/js/ui/views/scrollManagerView.es6.js',
            'rb/js/ui/views/userInfoboxView.es6.js',
            'rb/js/models/starManagerModel.es6.js',
            'rb/js/views/clientLoginView.es6.js',
            'rb/js/views/headerView.es6.js',
            'rb/js/views/collectionView.es6.js',
            'rb/js/views/starManagerView.es6.js',
        ),
        'output_filename': 'rb/js/base.min.js',
    },
    'ui': {
        'source_filenames': (
            'rb/js/ui/index.ts',
        ),
        'output_filename': 'rb/js/ui.min.js',
    },
    'account-page': {
        'source_filenames': (
            'rb/js/accountPrefsPage/index.ts',

            # Legacy JavaScript
            'rb/js/accountPrefsPage/views/apiTokensView.es6.js',
            'rb/js/accountPrefsPage/views/joinedGroupsView.es6.js',
            'rb/js/accountPrefsPage/views/oauthApplicationsView.es6.js',
            'rb/js/accountPrefsPage/views/oauthTokensView.es6.js',
        ),
        'output_filename': 'rb/js/account-page.min.js',
    },
    'config-forms': {
        'source_filenames': (
            'rb/js/configForms/index.ts',

            # Legacy JavaScript
            'rb/js/configForms/models/resourceListItemModel.es6.js',
        ),
        'output_filename': 'rb/js/config-forms.min.js',
    },
    'datagrid-pages': {
        'source_filenames': (
            'rb/js/datagrids/index.ts',

            # Legacy JavaScript
            'rb/js/pages/models/datagridPageModel.es6.js',
            'rb/js/pages/models/dashboardModel.es6.js',
            'rb/js/pages/views/datagridPageView.es6.js',
            'rb/js/pages/views/dashboardView.es6.js',
        ),
        'output_filename': 'rb/js/dashboard.min.js',
    },
    'reviews': {
        'source_filenames': (
            'rb/js/reviews/index.ts',

            # Legacy JavaScript
            #
            # Note: These are roughly in dependency order.
            'rb/js/models/uploadDiffModel.es6.js',
            'rb/js/utils/textUtils.es6.js',
            'rb/js/views/diffFragmentQueueView.es6.js',
            'rb/js/views/diffFragmentView.es6.js',
            'rb/js/views/draftReviewBannerView.es6.js',
            'rb/js/views/uploadAttachmentView.es6.js',
            'rb/js/views/revisionSelectorView.es6.js',
            'rb/js/views/fileAttachmentRevisionLabelView.es6.js',
            'rb/js/views/fileAttachmentRevisionSelectorView.es6.js',
            'rb/js/views/screenshotThumbnailView.es6.js',
            'rb/js/views/uploadDiffView.es6.js',
            'rb/js/views/updateDiffView.es6.js',
            'rb/js/diffviewer/models/commitHistoryDiffEntry.es6.js',
            'rb/js/diffviewer/models/diffCommitListModel.es6.js',
            'rb/js/diffviewer/models/diffCommitModel.es6.js',
            'rb/js/diffviewer/models/diffRevisionModel.es6.js',
            'rb/js/diffviewer/models/paginationModel.es6.js',
            'rb/js/diffviewer/collections/commitHistoryDiffEntryCollection.es6.js',
            'rb/js/diffviewer/collections/diffCommitCollection.es6.js',
            'rb/js/diffviewer/views/chunkHighlighterView.es6.js',
            'rb/js/diffviewer/views/diffCommitListView.es6.js',
            'rb/js/diffviewer/views/diffRevisionLabelView.es6.js',
            'rb/js/diffviewer/views/diffRevisionSelectorView.es6.js',
            'rb/js/diffviewer/views/paginationView.es6.js',
        ),
        'output_filename': 'rb/js/reviews.min.js',
    },
    'review-request-page': {
        'source_filenames': (
            'rb/js/reviewRequestPage/index.ts',

            # Legacy JavaScript
            'rb/js/reviewRequestPage/models/entryModel.es6.js',
            'rb/js/reviewRequestPage/models/reviewEntryModel.es6.js',
            'rb/js/reviewRequestPage/models/reviewReplyEditorModel.es6.js',
            'rb/js/reviewRequestPage/models/reviewRequestPageModel.es6.js',
            'rb/js/reviewRequestPage/models/statusUpdatesEntryModel.es6.js',
            'rb/js/reviewRequestPage/models/changeEntryModel.es6.js',
            'rb/js/reviewRequestPage/views/entryView.es6.js',
            'rb/js/reviewRequestPage/views/baseStatusUpdatesEntryView.es6.js',
            'rb/js/reviewRequestPage/views/changeEntryView.es6.js',
            'rb/js/reviewRequestPage/views/initialStatusUpdatesEntryView.es6.js',
            'rb/js/reviewRequestPage/views/issueSummaryTableView.es6.js',
            'rb/js/reviewRequestPage/views/reviewEntryView.es6.js',
            'rb/js/reviewRequestPage/views/reviewReplyEditorView.es6.js',
            'rb/js/reviewRequestPage/views/reviewRequestPageView.es6.js',
            'rb/js/reviewRequestPage/views/reviewView.es6.js',
        ),
        'output_filename': 'rb/js/review-request-page.min.js',
    },
    'newReviewRequest': {
        'source_filenames': (
            'rb/js/newReviewRequest/index.ts',

            # Legacy JavaScript
            #
            # Note: These are roughly in dependency order.
            'rb/js/models/uploadDiffModel.es6.js',
            'rb/js/newReviewRequest/models/postCommitModel.es6.js',
            'rb/js/newReviewRequest/models/newReviewRequestModel.es6.js',
            'rb/js/newReviewRequest/collections/repositoryCollection.es6.js',
            'rb/js/views/uploadDiffView.es6.js',
            'rb/js/newReviewRequest/views/branchView.es6.js',
            'rb/js/newReviewRequest/views/branchesView.es6.js',
            'rb/js/newReviewRequest/views/commitView.es6.js',
            'rb/js/newReviewRequest/views/commitsView.es6.js',
            'rb/js/newReviewRequest/views/repositoryView.es6.js',
            'rb/js/newReviewRequest/views/repositorySelectionView.es6.js',
            'rb/js/newReviewRequest/views/postCommitView.es6.js',
            'rb/js/newReviewRequest/views/preCommitView.es6.js',
            'rb/js/newReviewRequest/views/newReviewRequestView.es6.js',
        ),
        'output_filename': 'rb/js/newReviewRequest.min.js',
    },
    'oauth-edit': {
        'source_filenames': (
            # Legacy JavaScript
            'rb/js/accountPrefsPage/views/oauthClientSecretView.es6.js',
        ),
        'output_filename': 'rb/js/oauth.min.js',
    },
    'admin': {
        'source_filenames': (
            'rb/js/admin/index.ts',

            # Legacy JavaScript
            'lib/js/masonry-4.2.2.js',
            'rb/js/admin/models/changeListPageModel.es6.js',
            'rb/js/admin/models/dashboardPageModel.es6.js',
            'rb/js/admin/models/inlineFormGroupModel.es6.js',
            'rb/js/admin/models/inlineFormModel.es6.js',
            'rb/js/admin/models/widgetModel.es6.js',
            'rb/js/admin/models/newsWidgetModel.es6.js',
            'rb/js/admin/models/serverActivityWidgetModel.es6.js',
            'rb/js/admin/views/changeFormPageView.es6.js',
            'rb/js/admin/views/changeListPageView.es6.js',
            'rb/js/admin/views/dashboardPageView.es6.js',
            'rb/js/admin/views/inlineFormGroupView.es6.js',
            'rb/js/admin/views/inlineFormView.es6.js',
            'rb/js/admin/views/supportBannerView.es6.js',
            'rb/js/admin/views/widgetView.es6.js',
            'rb/js/admin/views/newsWidgetView.es6.js',
            'rb/js/admin/views/serverActivityWidgetView.es6.js',
            'rb/js/admin/views/userActivityWidgetView.es6.js',
        ),
        'output_filename': 'rb/js/admin.min.js',
    },
    'repositoryform': {
        'source_filenames': (
            # Legacy JavaScript
            'rb/js/admin/repositoryform.es6.js',
        ),
        'output_filename': 'rb/js/repositoryform.min.js',
    },
    'webhooks-form': {
        'source_filenames': (
            # Legacy JavaScript
            'rb/js/admin/views/webhookFormView.es6.js',
        ),
        'output_filename': 'rb/js/webhooks-form.min.js',
    },
    'widgets': {
        'source_filenames': (
            # Legacy JavaScript
            'rb/js/admin/views/relatedUserSelectorView.es6.js',
            'rb/js/admin/views/relatedRepoSelectorView.es6.js',
            'rb/js/admin/views/relatedGroupSelectorView.es6.js',
        ),
        'output_filename': 'rb/js/widgets.min.js',
    },
}


PIPELINE_STYLESHEETS = {
    'common': {
        'source_filenames': (
            'lib/css/3rdparty.less',
            'lib/css/jquery-ui-1.8.24.min.css',
            'lib/css/fontawesome.less',
            'rb/css/bundles/common.less',
        ),
        'output_filename': 'rb/css/common.min.css',
        'absolute_paths': False,
    },
    'js-tests': {
        'source_filenames': (
            'lib/css/jasmine-5.1.0.css',
            'rb/css/pages/js-tests.less',
        ),
        'output_filename': 'rb/css/js-tests.min.css',
        'absolute_paths': False,
    },
    'account-page': {
        'source_filenames': (
            'rb/css/pages/my-account.less',
        ),
        'output_filename': 'rb/css/account-page.min.css',
    },
    'reviews': {
        'source_filenames': (
            'rb/css/bundles/reviews.less',
        ),
        'output_filename': 'rb/css/reviews.min.css',
        'absolute_paths': False,
    },
    'newReviewRequest': {
        'source_filenames': (
            'rb/css/pages/newReviewRequest.less',
        ),
        'output_filename': 'rb/css/newReviewRequest.min.css',
        'absolute_paths': False,
    },
    'oauth': {
        'source_filenames': (
            'rb/css/pages/oauth.less',
        ),
        'output_filename': 'rb/css/oauth.min.css',
        'absolute_paths': False,
    },
    'admin': {
        'source_filenames': (
            'rb/css/bundles/admin.less',
        ),
        'output_filename': 'rb/css/admin.min.css',
        'absolute_paths': False,
    },
}
