CREATE
	UNIQUE INDEX profile_starred_review_requests__reviewrequest_profile
	ON accounts_profile_starred_review_requests
	(reviewrequest_id, profile_id);

