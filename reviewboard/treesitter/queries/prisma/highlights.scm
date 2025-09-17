
[
  "model"
  "datasource"
  "generator"
  "enum"
] @keyword

(string) @string
(string_char_escape) @string.special
(field_type) @type
(prisma_type) @type.builtin
(comment) @comment
(document_comment) @comment.document
(apply_function name: (identifier) @function)
(model_single_attribute label: (identifier) @variable.parameter)
(model_multi_attribute label: (identifier) @variable.parameter)
(integer) @number
(boolean) @constant.builtin
(special_constant) @constant.builtin

(attribute_specifier (identifier) @attribute)

[
  "@"
  "@@"
] @attribute

[
  ","
  "."
] @punctuation.delimiter

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket
