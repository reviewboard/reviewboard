; class
((annotation)? @class.outer
  .
  (class_definition
    body: (class_body) @class.inner) @class.outer)

(mixin_declaration
  (class_body) @class.inner) @class.outer

(enum_declaration
  body: (enum_body) @class.inner) @class.outer

(extension_declaration
  body: (extension_body) @class.inner) @class.outer

; function/method
((annotation)? @function.outer
  .
  [
    (method_signature)
    (function_signature)
  ] @function.outer
  .
  (function_body) @function.outer)

(type_alias
  (function_type)? @function.inner) @function.outer
