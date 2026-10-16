([
  (comment)
  (block_comment)
] @spell @comment)

[
  (label)
  (label_codeblock)
  (label_array)
] @string

((label) @keyword
  (#any-of? @keyword
    "null"
    "Null"
    "NULL"
  )
)

((label) @string.special
  (#any-of? @string.special
    "suspend"
    "unsuspend"
    "top-left"
    "top-center"
    "top-right"
    "center-left"
    "center-right"
    "bottom-left"
    "bottom-center"
    "bottom-right"
    "outside-top-left"
    "outside-top-center"
    "outside-top-right"
    "outside-left-center"
    "outside-right-center"
    "outside-bottom-left"
    "outside-bottom-center"
    "outside-bottom-right"
  )
)

((label_array) @constant
  (#any-of? @constant
    "primary_key"
    "PK"
    "foreign_key"
    "FK"
    "unique"
    "UNQ"
    "NULL"
    "NOT NULL"
  )
)

(escape) @string.escape

(identifier) @function
((identifier) @function.builtin
  (#any-of? @function.builtin
    "3d"
    "animated"
    "bold"
    "border-radius"
    "class"
    "classes"
    "constraint"
    "d2-config"
    "d2-legend"
    "direction"
    "double-border"
    "fill"
    "fill-pattern"
    "filled"
    "font"
    "font-color"
    "font-size"
    "height"
    "italic"
    "label"
    "layers"
    "level"
    "link"
    "multiple"
    "near"
    "opacity"
    "scenarios"
    "shadow"
    "shape"
    "source-arrowhead"
    "steps"
    "stroke"
    "stroke-dash"
    "stroke-width"
    "style"
    "target-arrowhead"
    "text-transform"
    "tooltip"
    "underline"
    "vars"
    "width"
  )
)

((identifier) @keyword
  (#eq? @keyword "_")
)

[
 "$"
 "...$"
 "@"
 "...@"
] @keyword

[
 (glob_filter)
 (inverse_glob_filter)
 (visibility_mark)
] @keyword.modifier

(import) @module

[(variable) (spread_variable)] @variable

(variable (identifier) @variable.member)
(variable (identifier_chain (identifier) @variable.member))

(spread_variable (identifier) @variable.member)
(spread_variable (identifier_chain (identifier) @variable.member))

[
  (glob)
  (recursive_glob)
  (global_glob)
] @string.special

(identifier
  (glob) @string.special.symbol)

(connection) @operator
(connection_identifier) @property
(integer) @number
(float) @number.float
(boolean) @boolean

(argument_name) @variable.parameter
(argument_type) @type

[
  "["
  "]"
  "("
  ")"
  "{"
  "}"
  "|"
  "||"
  "|||"
  "|`"
  "`|"
] @punctuation.bracket

[
  "."
  ","
  ":"
  ";"
] @punctuation.delimiter
