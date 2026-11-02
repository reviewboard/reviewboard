; Simple tokens ;;;;
(terminal) @string

(special_sequence) @string.special

(integer) @number

(comment) @comment @spell

; Identifiers ;;;;
; Allow different highlighting for specific casings
((identifier) @type
  (#match? @type "^[A-Z]"))

((identifier) @string.special.symbol
  (#match? @string.special.symbol "^[a-z]"))

((identifier) @constant
  (#match? @constant "^[A-Z][A-Z\\d_]+$"))

; Punctuation ;;;;
[
  ";"
  ","
] @punctuation.delimiter

[
  "|"
  "*"
  "-"
] @operator

"=" @keyword.operator

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket
