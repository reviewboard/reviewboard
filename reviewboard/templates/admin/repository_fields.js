  var BUG_TRACKER_FIELDS = { {% spaceless %}
{% for id, info in form.BUG_TRACKER_INFO.items %}
      "{{id}}": [ {% spaceless %}
{%  for field in info.fields %}
          "{{field}}"{% if not forloop.last %},{% endif %}
{%  endfor %}
      {% endspaceless %} ]{% if not forloop.last %},{% endif %}
{% endfor %}
  }{% endspaceless %}

  var HOSTING_SERVICE_FIELDS = { {% spaceless %}
{% for id, info in form.HOSTING_SERVICE_INFO.items %}
      "{{id}}": [ {% spaceless %}
{%  for field in info.fields %}
          "{{field}}"{% if not forloop.last %},{% endif %}
{%  endfor %}
      {% endspaceless %} ]{% if not forloop.last %},{% endif %}
{% endfor %}
  }{% endspaceless %}

  var HOSTING_SERVICE_HIDDEN_FIELDS = { {% spaceless %}
{% for id, info in form.HOSTING_SERVICE_INFO.items %}
      "{{id}}": [ {% spaceless %}
{%  for field in info.hidden_fields %}
          "{{field}}"{% if not forloop.last %},{% endif %}
{%  endfor %}
      {% endspaceless %} ]{% if not forloop.last %},{% endif %}
{% endfor %}
  }{% endspaceless %}

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
  }{% endspaceless %}

  var HOSTING_SERVICE_TOOLS = { {% spaceless %}
{% for id, info in form.HOSTING_SERVICE_INFO.items %}
      "{{id}}": [ {% spaceless %}
{%  for tool in info.tools %}
          "{{tool}}"{% if not forloop.last %},{% endif %}
{%  endfor %}
      {% endspaceless %} ]{% if not forloop.last %},{% endif %}
{% endfor %}
  }{% endspaceless %}

{% if form.hostkeyerror or form.certerror or adminform.userkeyerror %}
$(document).ready(function() {
  var inputs = $("fieldset, .submit-row").find("input, select");

  inputs.attr("disabled", true);

  $(".confirmation input").click(function() {
      inputs.attr("disabled", false);
  });
});
{% endif %}
