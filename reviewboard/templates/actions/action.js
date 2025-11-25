{% load actions %}

page.addActionView(new {{js_view_class}}({
    {% action_js_view_data_items action %}
    el:  $('#{{action.get_dom_element_id}}'),
    model: page.addAction(new {{js_model_class}}(
        {% action_js_model_data action %},
        { parse: true }
    ))
}));
