; ==============================================================================
; @attribute.inner
; @attribute.outer
; ==============================================================================
; @function.inner
; @function.outer
(proc_declaration
  body: (statement_list) @function.inner) @function.outer

(func_declaration
  body: (statement_list) @function.inner) @function.outer

(method_declaration
  body: (statement_list) @function.inner) @function.outer

(iterator_declaration
  body: (statement_list) @function.inner) @function.outer

(converter_declaration
  body: (statement_list) @function.inner) @function.outer

(template_declaration
  body: (statement_list) @function.inner) @function.outer

(macro_declaration
  body: (statement_list) @function.inner) @function.outer

(proc_expression
  body: (statement_list) @function.inner) @function.outer

(func_expression
  body: (statement_list) @function.inner) @function.outer

(iterator_expression
  body: (statement_list) @function.inner) @function.outer
