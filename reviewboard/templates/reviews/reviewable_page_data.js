{% load djblets_js reviewtags %}
        el: document.body,
        reviewRequestData: {
            bugTrackerURL: "{{review_request.repository.bug_tracker|escapejs}}",
            id: {{review_request.display_id}},
            localSitePrefix: "{% if review_request.local_site %}s/{{review_request.local_site.name}}/{% endif %}",
            branch: "{{review_request_details.branch|escapejs}}",
            bugsClosed: {{review_request_details.get_bug_list|json_dumps}},
            closeDescription: "{% normalize_text_for_edit close_description close_description_rich_text True %}",
            closeDescriptionRichText: {{close_description_rich_text|yesno:'true,false'}},
            description: "{% normalize_text_for_edit review_request_details.description review_request_details.description_rich_text True %}",
            descriptionRichText: {{review_request_details.description_rich_text|yesno:'true,false'}},
            hasDraft: {% if draft %}true{% else %}false{% endif %},
            lastUpdatedTimestamp: {{review_request.last_updated|json_dumps}},
            public: {% if review_request.public %}true{% else %}false{% endif %},
            reviewURL: "{{review_request.get_absolute_url|escapejs}}",
            state: RB.ReviewRequest.{% if review_request.status == 'P' %}PENDING{% elif review_request.status == 'D' %}CLOSE_DISCARDED{% elif review_request.status == 'S' %}CLOSE_SUBMITTED{% endif %},
            summary: "{{review_request_details.summary|escapejs}}",
            targetGroups: [{% spaceless %}
{% for group in review_request_details.target_groups.all %}
                {
                    name: "{{group.name|escapejs}}",
                    url: "{{group.get_absolute_url}}"
                }{% if not forloop.last %},{% endif %}
{% endfor %}{% endspaceless %}],
            targetPeople: [{% spaceless %}
{% for user in review_request_details.target_people.all %}
                {
                    username: "{{user.username|escapejs}}",
                    url: "{% url 'user' user %}"
                }{% if not forloop.last %},{% endif %}
{% endfor %}{% endspaceless %}],
            testingDone: "{% normalize_text_for_edit review_request_details.testing_done review_request_details.testing_done_rich_text True %}",
            testingDoneRichText: {{review_request_details.testing_done_rich_text|yesno:'true,false'}}
        },
        extraReviewRequestDraftData: {
{% if draft.changedesc %}
            changeDescription: "{% normalize_text_for_edit draft.changedesc.text draft.changedesc.rich_text True %}",
            changeDescriptionRichText: {{draft.changedesc.rich_text|yesno:'true,false'}}
{% endif %}
        },
        editorData: {
            mutableByUser: {{mutable_by_user|yesno:'true,false'}},
            statusMutableByUser: {{status_mutable_by_user|yesno:'true,false'}},
            fileAttachmentComments: {
{% if all_file_attachments %}
{%  for file_attachment in all_file_attachments %}
                {{file_attachment.id}}: {% file_attachment_comments file_attachment %}{% if not forloop.last %},{% endif %}
{%  endfor %}
{% endif %}
            }
        }
