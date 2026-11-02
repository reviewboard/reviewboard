(comment) @comment

(string) @string

(escape_sequence) @string.escape

(integer) @number

(decimal) @number

(true) @boolean

(false) @boolean

[
  "permit"
  "forbid"
  "when"
  "unless"
  "advice"
  "template"
] @keyword

[
  "if"
  "then"
  "else"
] @keyword.conditional

[
  "in"
  "has"
  "like"
  "is"
] @keyword.operator

[
  "principal"
  "action"
  "resource"
  "context"
] @variable

(slot
  "?" @punctuation.special
  (identifier) @variable.parameter)

[
  "=="
  "!="
  "<"
  "<="
  ">"
  ">="
  "=>"
  "&&"
  "||"
  "+"
  "-"
  "*"
  "/"
  "%"
  "!"
  "="
  "&"
  "|"
] @operator

[
  ","
  ";"
  "."
  ":"
  "::"
] @punctuation.delimiter

[
  "("
  ")"
  "{"
  "}"
  "["
  "]"
] @punctuation.bracket

(annotation
  "@" @punctuation.special
  (identifier) @attribute)

(extension_call
  (name
    (identifier) @function.builtin))

(method_call
  (identifier) @function.builtin)

(field_access
  (identifier) @property)

(record_entry
  (identifier) @property)

(attribute_declaration
  (identifier) @property)

(attribute_declaration
  "?" @punctuation.special)

(ref_init
  (identifier) @property)

(ref_init
  "-" @number)

(has_expression
  "has"
  .
  (identifier) @property)

(has_expression
  "has"
  .
  (member_expression
    .
    (identifier) @property))

(entity_reference
  (identifier) @type)

(type_reference
  (name
    (identifier) @type))

(scope_constraint
  "is"
  (name
    (identifier) @type))

(is_expression
  (name
    (identifier) @type))

(like_expression
  "like"
  .
  (string) @string.regexp)

(type_reference
  [
    "<"
    ">"
  ] @punctuation.bracket)
