suite('rb/models/uploadDiffModel', function() {
    var reviewRequest,
        updateDiffView;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 123
        });

        updateDiffView = new RB.UpdateDiffView({
            model: new RB.UploadDiffModel({
                changeNumber: reviewRequest.get('commitID'),
                repository: reviewRequest.get('repository'),
                reviewRequest: reviewRequest,
            }),
            el: $('#scratch')
        });
    });

    describe('Updating Review Requests', function() {
        it('"Start Over" doesn\'t change reviewRequest attribute', function() {
            spyOn(updateDiffView.model, 'startOver').andCallThrough();
            updateDiffView.model.startOver();

            expect(updateDiffView.model.attributes.reviewRequest).toBe(reviewRequest);
        });
    });
});