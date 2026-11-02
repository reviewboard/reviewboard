(comment) @comment

; Identifiers
;------------

; Escaped identifiers like \"+."
((value_identifier) @constant.macro
 (#match? @constant.macro "^\\.*$"))

[
  (type_identifier)
  (unit_type)
] @type


(list "[" @type)
(list_pattern "[" @type)

; To ensure that the closing curly bracket is the same color (scope) as the opening curly bracket
(list "]" @type (#set! "priority" 105))
(list_pattern "]" @type (#set! "priority" 105))

[
  (variant_identifier)
  (polyvar_identifier)
] @constant

(record_type_field (property_identifier) @property)
(record_field (property_identifier) @property)
(object (field (property_identifier) @property))
(object_type (field (property_identifier) @property))
(member_expression (property_identifier) @property)
(module_identifier) @namespace

; Parameters
;----------------

(list_pattern (value_identifier) @parameter)
(spread_pattern (value_identifier) @parameter)

; String literals
;----------------

[
  (string)
  (template_string)
] @string

(template_substitution
  "${" @punctuation.bracket
  "}" @punctuation.bracket) @embedded

(character) @string.special
(escape_sequence) @string.escape

; Other literals
;---------------

[
  (true)
  (false)
] @constant.builtin

(number) @number
(polyvar) @constant
(polyvar_string) @constant

; Functions
;----------

[
 (formal_parameters (value_identifier))
 (labeled_parameter (value_identifier))
] @parameter

(function parameter: (value_identifier) @parameter)

; Meta
;-----

[
 "[@"
 (decorator_identifier)
 "]"
] @annotation

(extension_identifier) @keyword
("%") @keyword

; Misc
;-----

(subscript_expression index: (string) @property)
(polyvar_type_pattern "`" @constant)

[
  ("include")
  ("open")
] @include

[
  "as"
  "export"
  "external"
  "let"
  "module"
  "mutable"
  "private"
  "rec"
  "type"
  "and"
  "assert"
  "async"
  "await"
  "with"
  "unpack"
] @keyword

[
  "if"
  "else"
  "switch"
  "when"
] @conditional

[
  "exception"
  "try"
  "catch"
] @exception

(call_expression
  function: (value_identifier) @exception
  (#eq? @exception "raise"))

[
  "for"
  "in"
  "to"
  "downto"
  "while"
] @repeat

[
  "."
  ","
  "|"
] @punctuation.delimiter

[
  "++"
  "+"
  "+."
  "-"
  "-."
  "*"
  "**"
  "*."
  "/."
  "<="
  "=="
  "==="
  "!"
  "!="
  "!=="
  ">="
  "&&"
  "||"
  "="
  ":="
  "->"
  "|>"
  ":>"
  (uncurry)
] @operator

; Explicitly enclose these operators with binary_expression
; to avoid confusion with JSX tag delimiters
(binary_expression ["<" ">" "/"] @operator)

[
  "("
  ")"
  "{"
  "}"
  "["
  "]"
  "[|"
  "|]"
] @punctuation.bracket

(polyvar_type
  [
   "["
   "[>"
   "[<"
   "]"
  "[|"
  "|]"
  ] @punctuation.bracket)

[
  "~"
  "?"
  "=>"
  ".."
  "..."
] @punctuation.special

(ternary_expression ["?" ":"] @operator)

; JSX
;----------
(jsx_identifier) @tag
(jsx_element
  open_tag: (jsx_opening_element ["<" ">"] @tag.delimiter))
(jsx_element
  close_tag: (jsx_closing_element ["<" "/" ">"] @tag.delimiter))
(jsx_self_closing_element ["/" ">" "<"] @tag.delimiter)
(jsx_fragment [">" "<" "/"] @tag.delimiter)
(jsx_attribute (property_identifier) @tag.attribute)

; Error
;----------

(ERROR) @error
