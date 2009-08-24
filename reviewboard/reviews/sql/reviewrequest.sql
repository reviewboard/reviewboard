CREATE
	UNIQUE INDEX reviewrequest_target_groups__reviewrequest_group
	ON reviews_reviewrequest_target_groups
	(reviewrequest_id, group_id);

CREATE
	INDEX reviewrequest_target_people__reviewrequest_user
	ON reviews_reviewrequest_target_people
	(reviewrequest_id, user_id);
