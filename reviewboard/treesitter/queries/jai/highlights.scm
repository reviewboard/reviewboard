; Includes

[
  (import)
  (load)
] @include


; Keywords
[
  ; from modules/Jai_Lexer
  "if"
  "xx"

  "ifx"
  "for"

  "then"
  "else"
  "null"
  "case"
  "enum"
  "true"
  "cast"

  "while"
  "break"
  "using"
  "defer"
  "false"
  "union"

  "return"
  "struct"
  "inline"
  "remove"

  ; "size_of"
  "type_of"
  ; "code_of"
  ; "context"

  "continue"
  "operator"

  ; "type_info"
  "no_inline"
  "interface"

  "enum_flags"

  ; "is_constant"

  "push_context"

  ; "initializer_of"
] @keyword

[
  "return"
] @keyword.return

[
  "if"
  "else"
  "case"
  "break"
] @conditional

((if_expression
  [
    "then"
    "ifx"
    "else"
  ] @conditional.ternary)
  (#set! "priority" 105))

; Repeats

[
  "for"
  "while"
  "continue"
] @repeat

; Variables

; (identifier) @variable
name: (identifier) @variable
argument: (identifier) @variable
named_argument: (identifier) @variable
(member_expression (identifier) @variable)
(parenthesized_expression (identifier) @variable)

((identifier) @variable.builtin
  (#any-of? @variable.builtin "context"))

; Namespaces

(import (identifier) @namespace)

; Parameters

(parameter (identifier) @parameter ":" "="? (identifier)? @constant)

; (call_expression argument: (identifier) @parameter "=")

; Functions

; (procedure_declaration (identifier) @function (procedure (block)))
(procedure_declaration (identifier) @function (block))

(call_expression function: (identifier) @function.call)

; Types

type: (types) @type
type: (identifier) @type
((types) @type)

modifier: (identifier) @keyword
keyword: (identifier) @keyword

((types (identifier) @type.builtin)
  (#any-of? @type.builtin
    "bool" "int" "string"
    "s8" "s16" "s32" "s64"
    "u8" "u16" "u32" "u64"
    "Type" "Any"))

(struct_declaration (identifier) @type ":" ":")

(enum_declaration (identifier) @type ":" ":")

; (const_declaration (identifier) @type ":" ":" [(array_type) (pointer_type)])

; ; I don't like this
; ((identifier) @type
;   (#lua-match? @type "^[A-Z][a-zA-Z0-9]*$")
;   (#not-has-parent? @type parameter procedure_declaration call_expression))

; Fields

(member_expression "." (identifier) @field)

(assignment_statement (identifier) @field "="?)
(update_statement (identifier) @field)

; Constants

((identifier) @constant
  (#match? @constant "^_*[A-Z][A-Z0-9_]*$")
  (#not-has-parent? @constant type parameter))

(member_expression . "." (identifier) @constant)

(enum_field (identifier) @constant)

; Literals

(integer) @number
(float) @number

(string) @string

;(character) @character

(string_contents (escape_sequence) @string.escape)

(boolean) @boolean

[
  (uninitialized)
  (null)
] @constant.builtin

; Operators

[
  ":"
  "="
  "+"
  "-"
  "*"
  "/"
  "%"
  ">"
  ">="
  "<"
  "<="
  "=="
  "!="
  "|"
  "~"
  "&"
  "&~"
  "<<"
  ">>"
  "<<<"
  ">>>"
  "||"
  "&&"
  "!"
  ".."
  "+="
  "-="
  "*="
  "/="
  "%="
  "&="
  "|="
  "^="
  "<<="
  ">>="
  "<<<="
  ">>>="
  "||="
  "&&="
] @operator

; Punctuation

[ "{" "}" ] @punctuation.bracket

[ "(" ")" ] @punctuation.bracket

[ "[" "]" ] @punctuation.bracket

[
  "`"
  "->"
  "."
  ","
  ":"
  ";"
] @punctuation.delimiter

; Comments

[
  (block_comment)
  (comment)
] @spell

[
  (block_comment)
  (comment)
] @comment 

; Tagged unions

(tagged_union_kind name: (identifier) @keyword)

(tagged_union_binding tag: (identifier) @constant)

",," @operator

; Errors

(ERROR) @error

directive: ("#") @keyword ; #if
type: ("type_of") @type

(compiler_directive) @keyword
(heredoc_start) @none
(heredoc_end) @none
(heredoc_body) @string
(note) @string
