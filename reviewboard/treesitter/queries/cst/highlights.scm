[
  ":"
  "-"
] @operator

[
  "`"
  "\""
] @punctuation.delimiter

"•" @punctuation.special

[
  "ERROR"
  "MISSING"
] @keyword

(number) @number

(kind) @type

name: _ @attribute

(literal
  (content) @string.special.symbol)

(text
  (content) @string)

escape: _ @string.escape
