/**
 * Bundle imports for Djblets, Review Board, and dependencies.
 *
 * Version Added:
 *     7.0
 */

/* We need all the third-party modules. */
import '../reviewboard/static/lib/js/3rdparty-base';
import '../reviewboard/static/lib/js/3rdparty';

/*
 * We also need all the built Djblets and Review Board bundles, so that we
 * have a RB namespace. Eventually, this can go away, hopefully.
 */
import '@beanbag/djblets/htdocs/static/djblets/js/jquery.gravy.min.js';
import '@beanbag/djblets/htdocs/static/djblets/js/utils.min.js';
import '@beanbag/djblets/htdocs/static/djblets/js/widgets.min.js';
import '@beanbag/djblets/htdocs/static/djblets/js/config-forms.min.js';
import '@beanbag/djblets/htdocs/static/djblets/js/extensions.min.js';
import '@beanbag/djblets/htdocs/static/djblets/js/integrations.min.js';
import '@beanbag/djblets/htdocs/static/djblets/js/forms.min.js';

import '../reviewboard/htdocs/static/rb/js/base.min.js';
import '../reviewboard/htdocs/static/rb/js/ui.min.js';
import '../reviewboard/htdocs/static/rb/js/config-forms.min.js';
import '../reviewboard/htdocs/static/rb/js/widgets.min.js';
import '../reviewboard/htdocs/static/rb/js/account-page.min.js';
import '../reviewboard/htdocs/static/rb/js/dashboard.min.js';
import '../reviewboard/htdocs/static/rb/js/reviews.min.js';
import '../reviewboard/htdocs/static/rb/js/review-request-page.min.js';
import '../reviewboard/htdocs/static/rb/js/newReviewRequest.min.js';
import '../reviewboard/htdocs/static/rb/js/oauth.min.js';
import '../reviewboard/htdocs/static/rb/js/admin.min.js';

/* And finally, all the CSS. */
import '../reviewboard/static/lib/css/3rdparty.less';
import '../reviewboard/static/lib/css/jquery-ui-1.8.24.min.css';
import '../reviewboard/static/lib/css/fontawesome.less';
import '../reviewboard/static/rb/css/bundles/common.less';
import '../reviewboard/static/rb/css/bundles/admin.less';
import '../reviewboard/static/rb/css/bundles/reviews.less';
