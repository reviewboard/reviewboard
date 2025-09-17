; Special identifiers
;--------------------
((symbol) @constant
 (#match? @constant "^[A-Z_][A-Z\\d_]+$"))

; Keyword
;---------
[
  "def"
  "var"
  "defn"
  "defn-"
  "varfn"
  "varfn-"
  "defmacro"
  "defmacro-"
  "do"
  "if"
  "fn"
  "break"
  "quote"
  "while"
  "splice"
  "unquote"
  "quasiquote"
  "upscope"
] @keyword

(set
  "set" @keyword)

(keyword) @variable.parameter
(symbol) @variable

; Function
;---------

(def
  name: (symbol) @function
  value: (fn))

(var
  name: (symbol) @function
  value: (fn))

(fn
  name: (symbol) @function)

(extra_defs
  name: (symbol) @function)

(tuple . item: (symbol) @function)

; Parameters
;---------
(parameters
  parameter: (symbol) @variable.parameter)

(tuple_parameters
  parameter: (symbol) @variable.parameter)

(parameters
  parameter: (tuple item: (symbol) @variable.parameter))

(tuple_parameters
  parameter: (tuple item: (symbol) @variable.parameter))

(parameters
  parameter: (sqr_tuple item: (symbol) @variable.parameter))

(tuple_parameters
  parameter: (sqr_tuple item: (symbol) @variable.parameter))

(parameters
  parameter: (array item: (symbol) @variable.parameter))

(tuple_parameters
  parameter: (array item: (symbol) @variable.parameter))

(parameters
  parameter: (sqr_array item: (symbol) @variable.parameter))

(tuple_parameters
  parameter: (sqr_array item: (symbol) @variable.parameter))

(parameters
  parameter: (struct value: (symbol) @variable.parameter))

(tuple_parameters
  parameter: (struct value: (symbol) @variable.parameter))

(parameters
  parameter: (table value: (symbol) @variable.parameter))

(tuple_parameters
  parameter: (table value: (symbol) @variable.parameter))

; Literals
;---------

(number_literal) @number

[
  (bool_literal)
  (nil_literal)
] @constant.builtin

[
  (str_literal)
  (long_str_literal)
  (buffer_literal)
  (long_buffer_literal)
] @string

(line_comment) @comment

[
  (variadic_marker)
  (optional_marker)
  (keys_marker)
] @property

; Special cases
; --------

(tuple
  .
  (symbol) @operator
  (.match? @operator "^(\\+|\\-|\\*|/|%|\\+\\+|\\+=|\\-\\-|\\-=|\\*=|/=|%=|and|or)$"))

(tuple
  .
  (symbol) @function.macro
  (.match? @function.macro "^(\\->|\\->>|\\-\\?>|\\-\\?>>|as\\->|as\\?\\->|case|chr|comment|compif|comptime|compwhen|cond|coro|default|defer|doc|each|eachk|eachp|eachy|edefer|for|forever|forv|generate|if-let|if-not|if-with|import|juxt|label|let|loop|match|prompt|protect|repeat|seq|short-fn|tracev|try|unless|use|when|when-let|when-with|with|with-dyns|with-syms|with-vars)$"))