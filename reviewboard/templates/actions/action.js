{% load actions %}

page.addActionView(new {{action.js_view_class}}({
    {% action_js_view_data_items action %}
    el: $('#{{action.get_dom_element_id}}'),
    model: new {{action.js_model_class}}(
        {% action_js_model_data action %},
        { parse: true })
}));
