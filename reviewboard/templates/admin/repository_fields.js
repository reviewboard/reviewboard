{% load djblets_js %}

var HOSTING_SERVICES = {{form.hosting_service_info|json_dumps:2}};

var TOOLS_FIELDS = { {% spaceless %}
    "none": [ "raw_file_url", "username", "password" ],
{% for tool in form.tool.field.queryset %}
    "{{tool.id}}": [ {% spaceless %}
{%  if tool.supports_raw_file_urls %}
         "raw_file_url",
{%  endif %}
         "username", "password"
    {% endspaceless %} ]{% if not forloop.last %},{% endif %}
{% endfor %}
};{% endspaceless %}

{% if form.hostkeyerror or form.certerror or adminform.userkeyerror %}
$(document).ready(function() {
  var inputs = $("fieldset, .submit-row").find("input, select");

  inputs.attr("disabled", true);

  $(".confirmation input").click(function() {
      inputs.attr("disabled", false);
  });
});
{% endif %}
