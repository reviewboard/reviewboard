{% load djblets_js %}

var HOSTING_SERVICES = {{form.hosting_service_info|json_dumps:2}};

var TOOLS_INFO = {
    "none": {
        fields: [ "raw_file_url", "username", "password" ],
    },

{% for tool in form.tool.field.queryset %}
    "{{tool.id}}": {
        fields: [ {% spaceless %}
{%  if tool.supports_raw_file_urls %}
           "raw_file_url",
{%  endif %}
           "username", "password"
        {% endspaceless %} ],
        help_text: {{tool.field_help_text|json_dumps:2}}
    }{% if not forloop.last %},{% endif %}
{% endfor %}
};

{% if form.hostkeyerror or form.certerror or adminform.userkeyerror %}
$(document).ready(function() {
  var inputs = $("fieldset, .submit-row").find("input, select");

  inputs.attr("disabled", true);

  $(".confirmation input").click(function() {
      inputs.attr("disabled", false);
  });
});
{% endif %}
