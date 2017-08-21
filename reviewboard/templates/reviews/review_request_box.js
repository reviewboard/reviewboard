{% load reviewtags %}

RB.PageManager.beforeRender(function(page) {
    var reviewRequestEditorView = page.reviewRequestEditorView,
        model = reviewRequestEditorView.model;

{% for_review_request_fieldset review_request_details %}
{%  for_review_request_field review_request_details fieldset %}
{%   if field.js_view_class %}
    reviewRequestEditorView.addFieldView(
        new {{field.js_view_class}}({
            el: $('#field_{{field.field_id|escapejs}}'),
            fieldID: '{{field.field_id|escapejs}}',
            model: model
        }));
{%   endif %}
{%  end_for_review_request_field %}
{% end_for_review_request_fieldset %}
});
