(tag_name) @tag @nospell

; (erroneous_end_tag_name) @error ; we do not lint syntax errors
(comment) @comment @spell

(attribute_name) @tag.attribute @nospell

(attribute_value) @nospell

((attribute
  (quoted_attribute_value) @string)
  (#set! priority 99))

(text) @none @spell

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading)
  (#eq? @_tag "title"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading.1)
  (#eq? @_tag "h1"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading.2)
  (#eq? @_tag "h2"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading.3)
  (#eq? @_tag "h3"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading.4)
  (#eq? @_tag "h4"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading.5)
  (#eq? @_tag "h5"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.heading.6)
  (#eq? @_tag "h6"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.strong)
  (#any-of? @_tag "strong" "b"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.italic)
  (#any-of? @_tag "em" "i"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.strikethrough)
  (#any-of? @_tag "s" "del"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.underline)
  (#eq? @_tag "u"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.raw)
  (#any-of? @_tag "code" "kbd"))

((element
  (start_tag
    (tag_name) @_tag)
  (text) @markup.link.label)
  (#eq? @_tag "a"))



[
  "<"
  ">"
  "</"
  "/>"
] @tag.delimiter

"=" @operator


(identifier) @variable

(style_unit) @variable

(pipe_operator) @operator

(string) @string

(number) @number

(pipe_call
  name: (identifier) @function)

(pipe_call
  arguments: (pipe_arguments
    (identifier) @variable.parameter))

(structural_directive
  "*" @keyword
  (identifier) @keyword)

(attribute
  (attribute_name) @variable.member
  (#match? @variable.member "(?s)#.*"))

(binding_name
  (identifier) @keyword)

(class_binding
  [
    (identifier)
    (class_name)
  ] @keyword)

(event_binding
  (binding_name
    (identifier) @keyword))

(event_binding
  "\"" @punctuation.delimiter)

(property_binding
  [
    "\""
    "\"\""
  ] @punctuation.delimiter)

(structural_assignment
  operator: (identifier) @keyword)

(member_expression
  property: (identifier) @property)

(call_expression
  function: (identifier) @function)

(call_expression
  function: ((identifier) @function.builtin
    (#eq? @function.builtin "$any")))

(pair
  key: ((identifier) @variable.builtin
    (#eq? @variable.builtin "$implicit")))

[
  (control_keyword)
  (special_keyword)
] @keyword

((control_keyword) @keyword.repeat
  (#any-of? @keyword.repeat "for" "empty"))

((control_keyword) @keyword.conditional
  (#any-of? @keyword.conditional "if" "else" "switch" "case" "default"))

((control_keyword) @keyword.coroutine
  (#any-of? @keyword.coroutine "defer" "placeholder" "loading"))

((control_keyword) @keyword.exception
  (#eq? @keyword.exception "error"))

((identifier) @boolean
  (#any-of? @boolean "true" "false"))

((identifier) @variable.builtin
  (#any-of? @variable.builtin "this" "$event"))

((identifier) @constant.builtin
  (#eq? @constant.builtin "null"))

[
  (ternary_operator)
  (conditional_operator)
] @keyword.conditional.ternary

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
  "@"
] @punctuation.bracket

(two_way_binding
  [
    "[("
    ")]"
  ] @punctuation.bracket)

[
  "{{"
  "}}"
] @punctuation.special

(template_substitution
  [
    "${"
    "}"
  ] @punctuation.special)

(template_chars) @string

[
  ";"
  "."
  ","
  "?."
  "!."
] @punctuation.delimiter

(nullish_coalescing_expression
  (coalescing_operator) @operator)

(concatenation_expression
  "+" @operator)

(icu_clause) @keyword.operator

(icu_category) @keyword.conditional

(binary_expression
  [
    "-"
    "&&"
    "+"
    "<"
    "<="
    "="
    "=="
    "==="
    "!="
    "!=="
    ">"
    ">="
    "*"
    "/"
    "||"
    "%"
  ] @operator)

(arrow_function
  "=>" @operator)

(object
  (spread
    "..." @punctuation.special))

(array
  (spread
    "..." @punctuation.special))

(arguments
  (spread
    "..." @punctuation.special))
