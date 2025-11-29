{% load actions %}

page.addAction(new {{js_model_class}}(
    {% action_js_model_data action %},
    { parse: true }
));
