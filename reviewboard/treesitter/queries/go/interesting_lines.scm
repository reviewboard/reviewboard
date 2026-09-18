; outer function textobject
(function_declaration) @function.outer

; outer function literals
(func_literal
  (_)?) @function.outer

; method as outer function textobject
(method_declaration
  body: (block)?) @function.outer

; struct and interface declaration as class textobject?
(type_declaration
  (type_spec
    (type_identifier)
    (struct_type
      (field_declaration_list
        (_)?) @class.inner))) @class.outer

(type_declaration
  (type_spec
    (type_identifier)
    (interface_type) @class.inner)) @class.outer

; struct literals as class textobject
(composite_literal
  (type_identifier)?
  (struct_type
    (_))?
  (literal_value
    (_)) @class.inner) @class.outer
