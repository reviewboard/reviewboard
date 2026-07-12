(function_declaration
  body: (statement_block)) @function.outer

(generator_function_declaration
  body: (statement_block)) @function.outer

(function_expression
  body: (statement_block)) @function.outer

(export_statement
  (function_declaration)) @function.outer

(arrow_function
  body: (_) @function.inner) @function.outer

(method_definition
  body: (statement_block)) @function.outer

(class_declaration
  body: (class_body)) @class.outer

(export_statement
  (class_declaration)) @class.outer
