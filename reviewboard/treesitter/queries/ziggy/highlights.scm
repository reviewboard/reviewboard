[
  (true)
  (false)
] @constant.builtin.boolean

(null) @constant.builtin
(number) @constant.numeric

(struct_field
  key: (_) @field)
  
(enum) @constant

[
  (string) 
  (line_string)*
] @string

(comment) @comment.line

(escape_sequence) @constant.character.escape

(ERROR) @error

"," @punctuation.delimiter

[
  "["
  "]"
  "{"
  "}"
  "("
  ")"
] @punctuation.bracket

[ "=" ":" ] @punctuation

