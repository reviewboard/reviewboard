window.RB = {};


$(document).ready(function() {
    $('.user').user_infobox();
    $('.bug').bug_infobox();
    $('.review-request-link').review_request_infobox();
    $('time.timesince').timesince();

    Djblets.enableRetinaImages();
});
