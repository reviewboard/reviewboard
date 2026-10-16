(start_symbol) @keyword
(hash_symbol) @punctuation.special

(open_paren) @punctuation.bracket
(close_paren) @punctuation.bracket
(open_brace) @punctuation.bracket
(close_brace) @punctuation.bracket

(semicolon) @punctuation.delimiter
(equals) @punctuation.delimiter

(string_line) @string

(continue_) @keyword.conditional
(break_) @keyword.conditional

(child_content_) @keyword

(as_) @keyword.operator
(as_clause
  alias: (component_tag_identifier) @type)
(
  (start_symbol) @keyword.import
  .
  (use_directive (use_) @keyword.import)
)

(number) @number
(bool) @boolean

(tag_open) @punctuation.bracket
(tag_close) @punctuation.bracket
(tag_end_open) @punctuation.bracket
(tag_self_close) @punctuation.bracket

(component_tag
  name: (component_tag_identifier) @tag)

(component_tag
  name_close: (component_tag_identifier) @tag)

(component_tag_parameter
  name: (rust_identifier) @variable.parameter)

(
  (start_symbol) @function.call
  .
  (rust_expr_simple)
)

(
  (start_symbol) @function.call
  .
  (rust_expr_paren)
)

(
  (start_symbol) @keyword.directive
  .
  (rust_block)
)

(
  (start_symbol) @keyword.conditional
  .
  (if_stmt)
)
(
  (start_symbol) @keyword
  .
  (for_stmt)
)
(
  (start_symbol) @keyword.repeat
  .
  (while_stmt)
)

(param_name) @variable.parameter
; (param_type) @type
; ((param_type) @type.builtin
;  (#match? @type.builtin "^&*(i32|u32|i64|f64|str|bool|char)$"))

;this is for now extra
(else_clause
  head: (rust_text) @keyword.conditional)
