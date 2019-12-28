{% load djblets_js %}

var HOSTING_SERVICES = {{form.hosting_service_info|json_dumps:2}},
    TOOLS_INFO = {{form.scmtool_info|json_dumps:2}};

{% if form.hostkeyerror or form.certerror or adminform.userkeyerror %}
$(function() {
    var $inputs = $('fieldset, .submit-row')
        .find('input, select')
        .prop('disabled', true);

    $('.confirmation input')
        .prop('disabled', false)
        .click(function() {
            $inputs.prop('disabled', false);
        });
});
{% endif %}
