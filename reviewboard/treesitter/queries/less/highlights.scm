(comment) @comment

(tag_name) @tag
(nesting_selector) @tag
(universal_selector) @tag

"~" @operator
">" @operator
"+" @operator
"-" @operator
"*" @operator
"/" @operator
"=" @operator
"^=" @operator
"|=" @operator
"~=" @operator
"$=" @operator
"*=" @operator

"and" @operator
"or" @operator
"not" @operator
"only" @operator

(attribute_selector (plain_value) @string)
(pseudo_element_selector (tag_name) @attribute)
(pseudo_class_selector (class_name) @attribute)

(class_name) @property
(id_name) @property
(namespace_name) @property
(property_name) @property
(feature_name) @property

(attribute_name) @attribute

(function_name) @function

((property_name) @variable
 (#match? @variable "^--"))
((plain_value) @variable
 (#match? @variable "^--"))

"@media" @keyword
"@import" @keyword
"@charset" @keyword
"@namespace" @keyword
"@supports" @keyword
(keyword) @keyword
(keyframes_statement (keyword) @keyword)
(at_keyword) @keyword
"to" @keyword
"from" @keyword
"!important" @keyword

(string_value) @string
(color_value) @string.special

(integer_value) @number
(float_value) @number
(unit) @type

[
 (color_value)]
@character

(string_value 
  (interpolated_variable) @string.escape)
@string

((property_name) @variable
 (#match? @variable "^--"))
((plain_value) @variable
 (#match? @variable "^--"))

(integer_value) @number
(float_value) @float

["true"
 "false"] @boolean

(variable_name) @variable
(params (variable) @parameter)
(params (keyword_param (variable) @parameter))

"#" @punctuation.delimiter
"," @punctuation.delimiter
":" @punctuation.delimiter
