
[
  "any"
  "struct"
  "union"
  "$"
] @keyword

[
  "?"
  "[]"
  "{:}"
] @type


(struct
  name: (_) @type)
(union
  name: (_) @type)

(expr (identifier) @type)
(identifier) @identifier

[
  "bool"
  "bytes"
  "int"
  "float"
] @constant.builtin

(doc_comment) @comment.line.documentation

(ERROR) @error

"," @punctuation.delimiter

":" @punctuation

[
  "{"
  "}"
] @punctuation.bracket
