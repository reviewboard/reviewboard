(class_declaration
  [
    (class_body)
    (enum_class_body)
  ]? @class.inner) @class.outer

[
  (function_declaration
    (function_body) @function.inner)
  (getter
    (function_body) @function.inner)
  (setter
    (function_body) @function.inner)
  (primary_constructor)
] @function.outer
