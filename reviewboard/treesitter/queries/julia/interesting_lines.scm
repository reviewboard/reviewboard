; Type definitions
(struct_definition) @class.outer

; Function definitions
(function_definition) @function.outer

(assignment
  (call_expression)
  (operator)
  (_) @function.inner) @function.outer

(arrow_function_expression
  [
    (identifier)
    (argument_list)
  ]
  "->"
  (_) @function.inner) @function.outer

(macro_definition) @function.outer
