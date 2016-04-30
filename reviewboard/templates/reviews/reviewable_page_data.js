{% load djblets_js djblets_utils reviewtags %}
        el: document.body,
        reviewRequestData: {
            bugTrackerURL: "{% if review_request.repository.bug_tracker %}{% url 'bug_url' review_request.display_id '--bug_id--' %}{% endif %}",
            id: {{review_request.display_id}},
            localSitePrefix: "{% if review_request.local_site %}s/{{review_request.local_site.name}}/{% endif %}",
            branch: "{{review_request_details.branch|escapejs}}",
            bugsClosed: {{review_request_details.get_bug_list|json_dumps}},
            closeDescription: "{% normalize_text_for_edit close_description close_description_rich_text True %}",
            closeDescriptionRichText: {{close_description_rich_text|yesno:'true,false'}},
            description: "{% normalize_text_for_edit review_request_details.description review_request_details.description_rich_text True %}",
            descriptionRichText: {{review_request_details.description_rich_text|yesno:'true,false'}},
            hasDraft: {{draft|yesno:'true,false'}},
            lastUpdatedTimestamp: {{review_request.last_updated|json_dumps}},
            public: {{review_request.public|yesno:'true,false'}},
{% if review_request.repository %}
            repository: new RB.Repository({
{%  with repo=review_request.repository %}
{%   with scmtool=repo.get_scmtool %}
                id: {{repo.id}},
                localSitePrefix: '{% if review_request.local_site %}s/{{review_request.local_site.name}}/{% endif %}',
                name: '{{repo.name|escapejs}}',
                requiresBasedir: {{scmtool.get_diffs_use_absolute_paths|yesno:'false,true'}},
                requiresChangeNumber: {{scmtool.supports_pending_changesets|yesno:'true,false'}},
                scmtoolName: '{{scmtool.name|escapejs}}',
                supportsPostCommit: {{repo.supports_post_commit|yesno:'true,false'}}
{%   endwith %}
{%  endwith %}
            }),
{% endif %}
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
            testingDoneRichText: {{review_request_details.testing_done_rich_text|yesno:'true,false'}},
{% if review_request_visit.visibility == 'V' %}
            visibility: RB.ReviewRequest.VISIBILITY_VISIBLE
{% elif review_request_visit.visibility == 'A' %}
            visibility: RB.ReviewRequest.VISIBILITY_ARCHIVED
{% elif review_request_visit.visibility == 'M' %}
            visibility: RB.ReviewRequest.VISIBILITY_MUTED
{% endif %}
        },
        extraReviewRequestDraftData: {
{% if draft.changedesc %}
{%  if draft.diffset %}
{%   url "view-interdiff" review_request.display_id draft.diffset.revision|add:"-1" draft.diffset.revision as interdiffLink %}
            interdiffLink: '{{interdiffLink|escapejs}}',
{%  endif %}
            changeDescription: "{% normalize_text_for_edit draft.changedesc.text draft.changedesc.rich_text True %}",
            changeDescriptionRichText: {{draft.changedesc.rich_text|yesno:'true,false'}}
{% endif %}
        },
        editorData: {
{% if draft.changedesc %}
            changeDescriptionRenderedText: '{{draft.changedesc.text|render_markdown:draft.changedesc.rich_text|escapejs}}',
{% endif %}
            closeDescriptionRenderedText: '{{close_description|render_markdown:close_description_rich_text|escapejs}}',
            hasDraft: {{draft|yesno:'true,false'}},
            mutableByUser: {{mutable_by_user|yesno:'true,false'}},
            statusMutableByUser: {{status_mutable_by_user|yesno:'true,false'}},
            showSendEmail: {{send_email|yesno:'true,false'}},
            fileAttachments: [
{% for file in file_attachments %}
{%  has_usable_review_ui request.user review_request file as use_review_ui %}
{%  definevar "caption" %}{% if draft %}{{file.draft_caption}}{% else %}{{file.caption}}{% endif %}{% enddefinevar %}
{%  definevar "file_attachment_url" %}{% if use_review_ui %}{% url "file-attachment" review_request.display_id file.pk %}{% endif %}{% enddefinevar %}
                {
                    id: {{file.pk}},
                    loaded: true,
                    attachmentHistoryID: {{file.attachment_history_id}},
                    caption: _.unescape('{{caption|escapejs}}'),
                    downloadURL: '{{file.get_absolute_url|escapejs}}',
                    filename: '{{file.filename|escapejs}}',
                    reviewURL: '{{file_attachment_url|escapejs}}',
                    revision: {{file.attachment_revision}},
                    thumbnailHTML: '{{file.thumbnail|escapejs}}'
                }{% if not forloop.last %},{% endif %}
{% endfor %}
            ],
            fileAttachmentComments: {
{% if all_file_attachments %}
{%  for file_attachment in all_file_attachments %}
                {{file_attachment.id}}: {% file_attachment_comments file_attachment %}{% if not forloop.last %},{% endif %}
{%  endfor %}
{% endif %}
            }
        },
        replyEditorData: {
            showSendEmail: {{send_email|yesno:'true,false'}}
        }
