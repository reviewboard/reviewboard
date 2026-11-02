(identifier) @variable


(comment) @comment
(string_literal) @string

[
    "||"
    "&&"
    "=="
    "!="
    "<"
    "<="
    ">"
    ">="
    "+"
    "-"
    "*"
    "/"
    "%"
    "\\"
    ".^"
    "%/%"
    ".*"
    "./"
    "!"
    "-"
    "+"
    "^"
    "'"
    "~"
    "="
    (assignment_op)
] @operator

[
    "("
    ")"
    "["
    "]"
    "{"
    "}"
    "<"
    ">"
] @punctuation.bracket

[
    ","
    "|"
    ";"
] @punctuation.delimiter

(function_declarator
name: (identifier) @function
)

(function_expression
name: (identifier) @function.call
)

(function_statement
name: (identifier) @function.call
)

(distr_expression
name: (identifier) @function.call
)

(sampling_statement
name: (identifier) @function.call
)

(print_statement
"print" @function.call)

(reject_statement
"reject" @function.call)

(fatal_error_statement
"fatal_error" @function.call)

[
    "data"
    "int"
    "real"
    "complex"
    "array"
    "tuple"
    "vector"
; BEGIN_STAN_ONLY
    "simplex"
    "unit_vector"
    "sum_to_zero_vector"
    "ordered"
    "positive_ordered"
    "row_vector"
    "matrix"
    "complex_vector"
    "complex_matrix"
    "complex_row_vector"
    "corr_matrix"
    "cov_matrix"
    "cholesky_factor_cov"
    "cholesky_factor_corr"
    "column_stochastic_matrix"
    "row_stochastic_matrix"
    "sum_to_zero_matrix"
; END_STAN_ONLY
    "void"
]@type

[
    (integer_literal)
    (real_literal)
    (imag_literal)
] @number

[
    "break"
    "continue"
    "while"
    "for"
    "if"
    "else"
    "return"
] @keyword.control

; BEGIN_STAN_ONLY
[
    "lower"
    "upper"
    "offset"
    "multiplier"
] @property
; END_STAN_ONLY

(preproc_include
    directive: "#include" @keyword
    file: (preproc_file) @string.special
)


(profile_statement "profile" @keyword)

(target_statement "target" @keyword "+=" @keyword)
(jacobian_statement "jacobian" @keyword "+=" @keyword)

(for_statement
loopvar: (identifier) @variable.parameter
)
(parameter_declaration
parameter: (identifier) @variable.parameter
)

; BEGIN_STAN_ONLY
; these probably shouldn't be modules
(functions "functions" @module)
(data "data" @module)
(transformed_data "transformed data" @module)
(parameters "parameters" @module)
(transformed_parameters "transformed parameters" @module)
(model "model" @module)
(generated_quantities "generated quantities" @module)
; END_STAN_ONLY
