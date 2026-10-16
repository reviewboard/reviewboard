; highlights.scm
[
  "!"
  "*"
  "/"
  "%"
  "+"
  "-"
  ">"
  ">="
  "<"
  "<="
  "=="
  "!="
  "&&"
  "||"
] @operator

[
  "{"
  "}"
  "["
  "]"
  "("
  ")"
] @punctuation.bracket

[
  "."
  ".*"
  ","
  "[*]"
] @punctuation.delimiter

[
  (ellipsis)
  "?"
  "=>"
] @punctuation.special

[
  ":"
  "="
] @none

[
  "for"
  "endfor"
  "in"
] @keyword.repeat

[
  "if"
  "else"
  "endif"
] @keyword.conditional

[
  (quoted_template_start) ; "
  (quoted_template_end) ; "
  (template_literal) ; non-interpolation/directive content
] @string

[
  (heredoc_identifier) ; END
  (heredoc_start) ; << or <<-
] @punctuation.delimiter

[
  (template_interpolation_start) ; ${
  (template_interpolation_end) ; }
  (template_directive_start) ; %{
  (template_directive_end) ; }
  (strip_marker) ; ~
] @punctuation.special

(numeric_lit) @number

(bool_lit) @boolean

(null_lit) @constant

(comment) @comment @spell

(identifier) @variable

(body
  (block
    (identifier) @keyword))

(body
  (block
    (body
      (block
        (identifier) @type))))

(function_call
  (identifier) @function)

(attribute
  (identifier) @variable.member)

; { key: val }
;
; highlight identifier keys as though they were block attributes
(object_elem
  key: (expression
    (variable_expr
      (identifier) @variable.member)))

; var.foo, data.bar
;
; first element in get_attr is a variable.builtin or a reference to a variable.builtin
(expression
  (variable_expr
    (identifier) @variable.builtin)
  (get_attr
    (identifier) @variable.member))


; Terraform specific references
;
;
; local/module/data/var/output
(expression
  (variable_expr
    (identifier) @variable.builtin
    (#any-of? @variable.builtin "data" "var" "local" "module" "output"))
  (get_attr
    (identifier) @variable.member))

; path.root/cwd/module
(expression
  (variable_expr
    (identifier) @type.builtin
    (#eq? @type.builtin "path"))
  (get_attr
    (identifier) @variable.builtin
    (#any-of? @variable.builtin "root" "cwd" "module")))

; terraform.workspace
(expression
  (variable_expr
    (identifier) @type.builtin
    (#eq? @type.builtin "terraform"))
  (get_attr
    (identifier) @variable.builtin
    (#eq? @variable.builtin "workspace")))

; Terraform specific keywords
; FIXME: ideally only for identifiers under a `variable` block to minimize false positives
((identifier) @type.builtin
  (#any-of? @type.builtin "bool" "string" "number" "object" "tuple" "list" "map" "set" "any"))

(object_elem
  val: (expression
    (variable_expr
      (identifier) @type.builtin
      (#any-of? @type.builtin "bool" "string" "number" "object" "tuple" "list" "map" "set" "any"))))
