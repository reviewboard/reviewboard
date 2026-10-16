; comments

[
  (eol_comment)
  (inline_comment)
] @comment

; words

(g_word) @keyword

[
  (axis_word)
  (indexed_axis_word)
] @number

(m_word) @constructor

(f_word) @module

(o_word) @keyword

(t_word) @tag

[
  (s_word)
  (spindle_select)
  (polar_distance)
] @attribute

[
  (parameter_word)
  (polar_angle)
] @property

(parameter_identifier) @property

(parameter_variable
(unsigned_integer) @property)

(property_name) @string

(other_word) @tag

(expression
  (number) @number)

(unary_expression
  (number) @number)

(binary_expression
  (number) @number)

(parameter_variable
  (number) @number)

; helpers
(line_number) @constant

(checksum) @operator

; operators, keywords and functions

[
 "eq"
 "ne"
 "gt"
 "ge"
 "lt"
 "le"
 "and"
 "or"
 "xor"
 "**"
 "mod"
 "/"
 "*"
 "-"
 "+"
 "="
] @operator

[
  "abs"
  "acos"
  "asin"
  "cos"
  "exp"
  "fix"
  "fup"
  "ln"
  "round"
  "sin"
  "sqrt"
  "tan"
  "exists"
  "atan"
  "bin"
  "bcd"
] @keyword.function

[
  "if"
  "else"
  "elseif"
  "endif"
  "goto"
  "then"
  "while"
  "endwhile"
  "do"
  "end"
  "call"
  "sub"
  "endsub"
  "repeat"
  "endrepeat"
  "continue"
  "break"
  "return"
] @keyword

; punctuation

[
 "["
 "]"
] @punctuation.bracket
