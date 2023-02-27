{% load djblets_js %}

page.addActionView(new {{action.js_view_class}}({
    {{action.get_js_view_data|json_dumps_items:','}}
    el: $('#{{action.get_dom_element_id}}'),
    model: new {{action.js_model_class}}(
        {{action.get_js_model_data|json_dumps}},
        { parse: true })
}));
