; Functions
; top level function with type annotation and doc comment
((module_declaration)
  (block_comment) @function.outer
  .
  (type_annotation)
  .
  (value_declaration
    body: (_)? @function.inner) @function.outer)

; top level function with type annotation
((module_declaration)
  (type_annotation) @function.outer
  .
  (value_declaration
    body: (_)? @function.inner) @function.outer)

; top level function without type annotation
((module_declaration)
  (value_declaration
    body: (_)? @function.inner) @function.outer)
