; Keywords

[
  "version"
  "import"
  "struct"
  "enum"
  "task"
  "workflow"
  "input"
  "output"
  "command"
  "runtime"
  "requirements"
  "hints"
  "meta"
  "parameter_meta"
] @keyword

[
  "if"
  "then"
  "else"
  "scatter"
  "call"
] @keyword

[
  "as"
  "alias"
  "in"
  "after"
  "object"
  "env"
] @keyword

; Types

(primitive_type) @type.builtin

[
  "Array"
  "Map"
  "Pair"
] @type.builtin

(object_type) @type.builtin

(user_type
  (identifier) @type)

; Literals

(boolean_literal) @boolean
[
  (null_literal)
  (none_literal)
  (left_literal)
  (right_literal)
] @constant.builtin
(integer_literal) @number
(float_literal) @number
(meta_number) @number

; Strings

(single_quoted_string) @string
(double_quoted_string) @string
(multi_line_string) @string
(string_text_single) @string
(string_text_double) @string
(multi_line_string_text) @string
(escape_sequence) @string.escape

; Placeholders

(placeholder
  ["~{" "${"] @punctuation.special
  "}" @punctuation.special)

(string_placeholder
  ["~{" "${"] @punctuation.special
  "}" @punctuation.special)

; Comments

(comment) @comment

; Version

(version_identifier) @number

; Operators

[
  "="
  "=="
  "!="
  "<"
  "<="
  ">"
  ">="
  "+"
  "-"
  "*"
  "/"
  "%"
  "||"
  "&&"
  "!"
  "?"
] @operator

; Punctuation

[
  "{"
  "}"
  "["
  "]"
  "("
  ")"
  "<<<"
  ">>>"
] @punctuation.bracket

[
  ","
  ":"
  "."
] @punctuation.delimiter

; Definitions

(struct
  (identifier) @type.definition)

(enum
  (identifier) @type.definition)

(task
  (identifier) @function.definition)

(workflow
  (identifier) @function.definition)

; Declarations

(declaration
  (identifier) @variable)

(bound_declaration
  (identifier) @variable)

; Meta

(meta_attribute
  (identifier) @property)

(runtime_attribute
  (identifier) @property)

; Call

(call
  (qualified_identifier) @function)

(call_input
  (identifier) @variable)

; Scatter

(scatter
  "(" (identifier) @variable "in")

; Functions

(apply_expression
  (identifier) @function.builtin)

; Member access

(member_expression
  "." (identifier) @property)

; Import

(import
  "as" (identifier) @namespace)

(import_alias
  (identifier) @function . "as" (identifier) @function)

; Struct literal

(struct_literal
  (identifier) @type)

(object_field
  (identifier) @property)
