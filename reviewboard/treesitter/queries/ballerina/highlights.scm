
"ascending" @keyword
"break" @keyword
"by" @keyword
"check" @keyword
"checkpanic" @keyword
"class" @keyword
"client" @keyword
"conflict" @keyword
"const" @keyword
"descending" @keyword
"distinct" @keyword
"else" @keyword
"equals"@keyword
"final" @keyword
"foreach" @keyword
"from" @keyword
"function" @keyword
"if" @keyword
"import" @keyword
"in" @keyword
"isolated" @keyword
"join" @keyword
"let" @keyword
"limit" @keyword
"on" @keyword
"on" @keyword
"order" @keyword
"outer" @keyword
"private" @keyword
"public" @keyword
"readonly" @keyword
"remote" @keyword
"return" @keyword
"returns" @keyword
"select" @keyword
"service" @keyword
"type" @keyword
"var" @keyword
"where" @keyword
"while" @keyword

";" @delimiter
":" @delimiter

"=" @operator
"==" @operator
"!=" @operator
"<" @operator
"<=" @operator
">" @operator
">=" @operator
"+" @operator
"-" @operator
"*" @operator
"/" @operator
"%" @operator
"==" @operator
"?" @operator

(type_desc) @type
(builtin_type_name) @type.builtin

(function_defn (identifier) @function)
(method_defn (identifier) @function)
(method_decl (identifier) @function)
(function_call_expr (function_reference) @function)
(method_call_expr (identifier) @function.method)

(string_literal) @string

(int_literal) @number
(floating_point_literal) @number

(field_name) @property
(field_access_lvexpr (identifier) @property)
(field_access_expr (expression) @property)

(comment) @comment
