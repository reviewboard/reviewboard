; Methods

(method
  exemplarname: (identifier) @type)
(method
  name: (identifier) @function.method)

; Literals

[
  (number)
] @number

[
  (string_literal)
] @string

[
  (true)
  (false)
  (maybe)
  (unset)
] @constant.builtin

[
 (self)
 (super)
 (clone)
] @variable.builtin

[
 (symbol)
 (character_literal)
] @constant

(documentation) @attribute
(comment) @comment
(pragma) @attribute

; Expression

(call
  receiver: (variable) @variable.parameter)
(call 
  operator: "." @operator)
(call
  message: (identifier) @function)

; Keywords

[
  "_method"
  "_endmethod"

  "_block"
  "_endblock"

  "_if"
  "_then"
  "_elif"
  "_else"
  "_endif"
  
  "_return"
] @keyword
