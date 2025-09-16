; Types
; Javascript
; Variables
;-----------
(identifier) @variable

; Properties
;-----------
(property_identifier) @variable.member

(shorthand_property_identifier) @variable.member

(private_property_identifier) @variable.member

(object_pattern
  (shorthand_property_identifier_pattern) @variable)

(object_pattern
  (object_assignment_pattern
    (shorthand_property_identifier_pattern) @variable))

; Special identifiers
;--------------------
((identifier) @type
  (#match? @type "^[A-Z]"))

((identifier) @constant
  (#match? @constant "^_*[A-Z][A-Z\\d_]*$"))

((shorthand_property_identifier) @constant
  (#match? @constant "^_*[A-Z][A-Z\\d_]*$"))

((identifier) @variable.builtin
  (#any-of? @variable.builtin "arguments" "module" "console" "window" "document"))

((identifier) @type.builtin
  (#any-of? @type.builtin
    "Object" "Function" "Boolean" "Symbol" "Number" "Math" "Date" "String" "RegExp" "Map" "Set"
    "WeakMap" "WeakSet" "Promise" "Array" "Int8Array" "Uint8Array" "Uint8ClampedArray" "Int16Array"
    "Uint16Array" "Int32Array" "Uint32Array" "Float32Array" "Float64Array" "ArrayBuffer" "DataView"
    "Error" "EvalError" "InternalError" "RangeError" "ReferenceError" "SyntaxError" "TypeError"
    "URIError"))

(statement_identifier) @label

; Function and method definitions
;--------------------------------
(function_expression
  name: (identifier) @function)

(function_declaration
  name: (identifier) @function)

(generator_function
  name: (identifier) @function)

(generator_function_declaration
  name: (identifier) @function)

(method_definition
  name: [
    (property_identifier)
    (private_property_identifier)
  ] @function.method)

(method_definition
  name: (property_identifier) @constructor
  (#eq? @constructor "constructor"))

(pair
  key: (property_identifier) @function.method
  value: (function_expression))

(pair
  key: (property_identifier) @function.method
  value: (arrow_function))

(assignment_expression
  left: (member_expression
    property: (property_identifier) @function.method)
  right: (arrow_function))

(assignment_expression
  left: (member_expression
    property: (property_identifier) @function.method)
  right: (function_expression))

(variable_declarator
  name: (identifier) @function
  value: (arrow_function))

(variable_declarator
  name: (identifier) @function
  value: (function_expression))

(assignment_expression
  left: (identifier) @function
  right: (arrow_function))

(assignment_expression
  left: (identifier) @function
  right: (function_expression))

; Function and method calls
;--------------------------
(call_expression
  function: (identifier) @function.call)

(call_expression
  function: (member_expression
    property: [
      (property_identifier)
      (private_property_identifier)
    ] @function.method.call))

(call_expression
  function: (await_expression
    (identifier) @function.call))

(call_expression
  function: (await_expression
    (member_expression
      property: [
        (property_identifier)
        (private_property_identifier)
      ] @function.method.call)))

; Builtins
;---------
((identifier) @module.builtin
  (#eq? @module.builtin "Intl"))

((identifier) @function.builtin
  (#any-of? @function.builtin
    "eval" "isFinite" "isNaN" "parseFloat" "parseInt" "decodeURI" "decodeURIComponent" "encodeURI"
    "encodeURIComponent" "require"))

; Constructor
;------------
(new_expression
  constructor: (identifier) @constructor)

; Decorators
;----------
(decorator
  "@" @attribute
  (identifier) @attribute)

(decorator
  "@" @attribute
  (call_expression
    (identifier) @attribute))

(decorator
  "@" @attribute
  (member_expression
    (property_identifier) @attribute))

(decorator
  "@" @attribute
  (call_expression
    (member_expression
      (property_identifier) @attribute)))

; Literals
;---------
[
  (this)
  (super)
] @variable.builtin

((identifier) @variable.builtin
  (#eq? @variable.builtin "self"))

[
  (true)
  (false)
] @boolean

[
  (null)
  (undefined)
] @constant.builtin

[
  (comment)
  (html_comment)
] @comment @spell

((comment) @comment.documentation
  (#match? @comment.documentation "(?s)^/[*][*][^*].*[*]/$"))

(hash_bang_line) @keyword.directive

((string_fragment) @keyword.directive
  (#eq? @keyword.directive "use strict"))

(string) @string

(template_string) @string

(escape_sequence) @string.escape

(regex_pattern) @string.regexp

(regex_flags) @character.special

(regex
  "/" @punctuation.bracket) ; Regex delimiters

(number) @number

((identifier) @number
  (#any-of? @number "NaN" "Infinity"))

; Punctuation
;------------
[
  ";"
  "."
  ","
  ":"
] @punctuation.delimiter

[
  "--"
  "-"
  "-="
  "&&"
  "+"
  "++"
  "+="
  "&="
  "/="
  "**="
  "<<="
  "<"
  "<="
  "<<"
  "="
  "=="
  "==="
  "!="
  "!=="
  "=>"
  ">"
  ">="
  ">>"
  "||"
  "%"
  "%="
  "*"
  "**"
  ">>>"
  "&"
  "|"
  "^"
  "??"
  "*="
  ">>="
  ">>>="
  "^="
  "|="
  "&&="
  "||="
  "??="
  "..."
] @operator

(binary_expression
  "/" @operator)

(ternary_expression
  [
    "?"
    ":"
  ] @keyword.conditional.ternary)

(unary_expression
  [
    "!"
    "~"
    "-"
    "+"
  ] @operator)

(unary_expression
  [
    "delete"
    "void"
  ] @keyword.operator)

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket

(template_substitution
  [
    "${"
    "}"
  ] @punctuation.special) @none

; Imports
;----------
(namespace_import
  "*" @character.special
  (identifier) @module)

(namespace_export
  "*" @character.special
  (identifier) @module)

(export_statement
  "*" @character.special)

; Keywords
;----------
[
  "if"
  "else"
  "switch"
  "case"
] @keyword.conditional

[
  "import"
  "from"
  "as"
  "export"
] @keyword.import

[
  "for"
  "of"
  "do"
  "while"
  "continue"
] @keyword.repeat

[
  "break"
  "const"
  "debugger"
  "extends"
  "get"
  "let"
  "set"
  "static"
  "target"
  "var"
  "with"
] @keyword

"class" @keyword.type

[
  "async"
  "await"
] @keyword.coroutine

[
  "return"
  "yield"
] @keyword.return

"function" @keyword.function

[
  "new"
  "delete"
  "in"
  "instanceof"
  "typeof"
] @keyword.operator

[
  "throw"
  "try"
  "catch"
  "finally"
] @keyword.exception

(export_statement
  "default" @keyword)

(switch_default
  "default" @keyword.conditional)

(jsx_element
  open_tag: (jsx_opening_element
    [
      "<"
      ">"
    ] @tag.delimiter))

(jsx_element
  close_tag: (jsx_closing_element
    [
      "</"
      ">"
    ] @tag.delimiter))

(jsx_self_closing_element
  [
    "<"
    "/>"
  ] @tag.delimiter)

(jsx_attribute
  (property_identifier) @tag.attribute)

(jsx_opening_element
  name: (identifier) @tag.builtin)

(jsx_closing_element
  name: (identifier) @tag.builtin)

(jsx_self_closing_element
  name: (identifier) @tag.builtin)

(jsx_opening_element
  ((identifier) @tag
    (#match? @tag "^[A-Z]")))

; Handle the dot operator effectively - <My.Component>
(jsx_opening_element
  (member_expression
    (identifier) @tag.builtin
    (property_identifier) @tag))

(jsx_closing_element
  ((identifier) @tag
    (#match? @tag "^[A-Z]")))

; Handle the dot operator effectively - </My.Component>
(jsx_closing_element
  (member_expression
    (identifier) @tag.builtin
    (property_identifier) @tag))

(jsx_self_closing_element
  ((identifier) @tag
    (#match? @tag "^[A-Z]")))

; Handle the dot operator effectively - <My.Component />
(jsx_self_closing_element
  (member_expression
    (identifier) @tag.builtin
    (property_identifier) @tag))

(html_character_reference) @tag

(jsx_text) @none @spell

(html_character_reference) @character.special

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading)
  (#eq? @_tag "title"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading.1)
  (#eq? @_tag "h1"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading.2)
  (#eq? @_tag "h2"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading.3)
  (#eq? @_tag "h3"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading.4)
  (#eq? @_tag "h4"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading.5)
  (#eq? @_tag "h5"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.heading.6)
  (#eq? @_tag "h6"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.strong)
  (#any-of? @_tag "strong" "b"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.italic)
  (#any-of? @_tag "em" "i"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.strikethrough)
  (#any-of? @_tag "s" "del"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.underline)
  (#eq? @_tag "u"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.raw)
  (#any-of? @_tag "code" "kbd"))

((jsx_element
  (jsx_opening_element
    name: (identifier) @_tag)
  (jsx_text) @markup.link.label)
  (#eq? @_tag "a"))

((jsx_attribute
  (property_identifier) @_attr
  (string
    (string_fragment) @string.special.url))
  (#any-of? @_attr "href" "src"))






; Parameters
(formal_parameters
  (identifier) @variable.parameter)

(formal_parameters
  (rest_pattern
    (identifier) @variable.parameter))

; ({ a }) => null
(formal_parameters
  (object_pattern
    (shorthand_property_identifier_pattern) @variable.parameter))

; ({ a = b }) => null
(formal_parameters
  (object_pattern
    (object_assignment_pattern
      (shorthand_property_identifier_pattern) @variable.parameter)))

; ({ a: b }) => null
(formal_parameters
  (object_pattern
    (pair_pattern
      value: (identifier) @variable.parameter)))

; ([ a ]) => null
(formal_parameters
  (array_pattern
    (identifier) @variable.parameter))

; ({ a } = { a }) => null
(formal_parameters
  (assignment_pattern
    (object_pattern
      (shorthand_property_identifier_pattern) @variable.parameter)))

; ({ a = b } = { a }) => null
(formal_parameters
  (assignment_pattern
    (object_pattern
      (object_assignment_pattern
        (shorthand_property_identifier_pattern) @variable.parameter))))

; a => null
(arrow_function
  parameter: (identifier) @variable.parameter)

; optional parameters
(formal_parameters
  (assignment_pattern
    left: (identifier) @variable.parameter))

; punctuation
(optional_chain) @punctuation.delimiter
