{% load actions %}

page.addActionView(new {{js_view_class}}({
    {% action_js_view_data_items action %}
    el: $('#{{dom_element_id}}'),
    model: page.getAction("{{action.action_id}}"),
}));
