{% load djblets_js %}

var HOSTING_SERVICES = {{form.hosting_service_info|json_dumps:2}},
    TOOLS_INFO = {{form.tool_info|json_dumps:2}};

{% if form.hostkeyerror or form.certerror or adminform.userkeyerror %}
$(document).ready(function() {
  var inputs = $("fieldset, .submit-row").find("input, select");

  inputs.prop("disabled", true);
  $(".confirmation input")
      .prop("disabled", false);
      .click(function() {
          inputs.prop("disabled", false);
      });
});
{% endif %}
