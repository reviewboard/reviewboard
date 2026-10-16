[
  "schema"
  "protocol"
  "import"
  "fixed"
  "record"
  "error"
  "enum"
  "throws"
  "namespace"
  "union"
  (oneway)
] @keyword

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
  "<"
  ">"
]  @punctuation.bracket

[
  ";"
  ","
] @punctuation.delimiter

(comment) @comment

[
  (field_declaration name: (identifier))
  (parameter name: (identifier))
  (default_value_expression left: (identifier))
  (throw_statement (identifier))
] @variable

[
  (enumeral (identifier))
] @variant

[
  (primitive_type)
  (logical_type (identifier))
  (logical_type (call_expression (identifier)))
] @type

[
  (string)
  (literal_type (string))
] @string

[
  (literal_type (number))
] @number

[
  (void)
  (true)
  (false)
  (null)
] @constant.builtin

[
  (default_enumeral (identifier))
] @constant

[
  (known_logical_type)
  (map)
  (array)
] @function.builtin

[
  (rpc_message_declaration name: (identifier))
  (fixed_declaration (identifier))
  (fixed_declaration (call_expression (identifier)))
] @function

(anotation_statement name: (anotation_identifier) @attribute)

(record_declaration
  name: (identifier) @constructor)

(error_declaration
  name: (identifier) @constructor)

(enum_declaration
  name: (identifier) @constructor)

(protocol_declaration
  name: (identifier) @constructor)
