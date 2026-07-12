; named function
(binding
  (function_expression)) @function.outer

; anonymous function
(function_expression
  (_) ; argument
  (_) @function.inner) @function.outer
