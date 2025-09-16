; Lower priority to prefer @variable.parameter when identifier appears in parameter_declaration.
((identifier) @variable
  (#set! priority 95))

(preproc_def
  (preproc_arg) @variable)

[
  "default"
  "goto"
  "asm"
  "__asm__"
] @keyword

[
  "enum"
  "struct"
  "union"
  "typedef"
] @keyword.type

[
  "sizeof"
  "offsetof"
] @keyword.operator

(alignof_expression
  .
  _ @keyword.operator)

"return" @keyword.return

[
  "while"
  "for"
  "do"
  "continue"
  "break"
] @keyword.repeat

[
  "if"
  "else"
  "case"
  "switch"
] @keyword.conditional

[
  "#if"
  "#ifdef"
  "#ifndef"
  "#else"
  "#elif"
  "#endif"
  "#elifdef"
  "#elifndef"
  (preproc_directive)
] @keyword.directive

"#define" @keyword.directive.define

"#include" @keyword.import

[
  ";"
  ":"
  ","
  "."
  "::"
] @punctuation.delimiter

"..." @punctuation.special

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket

[
  "="
  "-"
  "*"
  "/"
  "+"
  "%"
  "~"
  "|"
  "&"
  "^"
  "<<"
  ">>"
  "->"
  "<"
  "<="
  ">="
  ">"
  "=="
  "!="
  "!"
  "&&"
  "||"
  "-="
  "+="
  "*="
  "/="
  "%="
  "|="
  "&="
  "^="
  ">>="
  "<<="
  "--"
  "++"
] @operator

; Make sure the comma operator is given a highlight group after the comma
; punctuator so the operator is highlighted properly.
(comma_expression
  "," @operator)

[
  (true)
  (false)
] @boolean

(conditional_expression
  [
    "?"
    ":"
  ] @keyword.conditional.ternary)

(string_literal) @string

(system_lib_string) @string

(escape_sequence) @string.escape

(null) @constant.builtin

(number_literal) @number

(char_literal) @character

(preproc_defined) @function.macro

((field_expression
  (field_identifier) @property) @_parent
  (#not-has-parent? @_parent template_method function_declarator call_expression))

(field_designator) @property

((field_identifier) @property
  (#has-ancestor? @property field_declaration)
  (#not-has-ancestor? @property function_declarator))

(statement_identifier) @label

(declaration
  type: (type_identifier) @_type
  declarator: (identifier) @label
  (#eq? @_type "__label__"))

[
  (type_identifier)
  (type_descriptor)
] @type

(storage_class_specifier) @keyword.modifier

[
  (type_qualifier)
  (gnu_asm_qualifier)
  "__extension__"
] @keyword.modifier

(linkage_specification
  "extern" @keyword.modifier)

(type_definition
  declarator: (type_identifier) @type.definition)

(primitive_type) @type.builtin

(sized_type_specifier
  _ @type.builtin
  type: _?)

((identifier) @constant
  (#match? @constant "^[A-Z][A-Z0-9_]+$"))

(preproc_def
  (preproc_arg) @constant
  (#match? @constant "^[A-Z][A-Z0-9_]+$"))

(enumerator
  name: (identifier) @constant)

(case_statement
  value: (identifier) @constant)

((identifier) @constant.builtin
  ; format-ignore
  (#any-of? @constant.builtin
    "stderr" "stdin" "stdout"
    "__FILE__" "__LINE__" "__DATE__" "__TIME__"
    "__STDC__" "__STDC_VERSION__" "__STDC_HOSTED__"
    "__cplusplus" "__OBJC__" "__ASSEMBLER__"
    "__BASE_FILE__" "__FILE_NAME__" "__INCLUDE_LEVEL__"
    "__TIMESTAMP__" "__clang__" "__clang_major__"
    "__clang_minor__" "__clang_patchlevel__"
    "__clang_version__" "__clang_literal_encoding__"
    "__clang_wide_literal_encoding__"
    "__FUNCTION__" "__func__" "__PRETTY_FUNCTION__"
    "__VA_ARGS__" "__VA_OPT__"))

(preproc_def
  (preproc_arg) @constant.builtin
  ; format-ignore
  (#any-of? @constant.builtin
    "stderr" "stdin" "stdout"
    "__FILE__" "__LINE__" "__DATE__" "__TIME__"
    "__STDC__" "__STDC_VERSION__" "__STDC_HOSTED__"
    "__cplusplus" "__OBJC__" "__ASSEMBLER__"
    "__BASE_FILE__" "__FILE_NAME__" "__INCLUDE_LEVEL__"
    "__TIMESTAMP__" "__clang__" "__clang_major__"
    "__clang_minor__" "__clang_patchlevel__"
    "__clang_version__" "__clang_literal_encoding__"
    "__clang_wide_literal_encoding__"
    "__FUNCTION__" "__func__" "__PRETTY_FUNCTION__"
    "__VA_ARGS__" "__VA_OPT__"))

(attribute_specifier
  (argument_list
    (identifier) @variable.builtin))

(attribute_specifier
  (argument_list
    (call_expression
      function: (identifier) @variable.builtin)))

((call_expression
  function: (identifier) @function.builtin)
  (#match? @function.builtin "^__builtin_"))

((call_expression
  function: (identifier) @function.builtin)
  (#has-ancestor? @function.builtin attribute_specifier))

; Preproc def / undef
(preproc_def
  name: (_) @constant.macro)

(preproc_call
  directive: (preproc_directive) @_u
  argument: (_) @constant.macro
  (#eq? @_u "#undef"))

(preproc_ifdef
  name: (identifier) @constant.macro)

(preproc_elifdef
  name: (identifier) @constant.macro)

(preproc_defined
  (identifier) @constant.macro)

(call_expression
  function: (identifier) @function.call)

(call_expression
  function: (field_expression
    field: (field_identifier) @function.call))

(function_declarator
  declarator: (identifier) @function)

(function_declarator
  declarator: (parenthesized_declarator
    (pointer_declarator
      declarator: (field_identifier) @function)))

(preproc_function_def
  name: (identifier) @function.macro)

(comment) @comment @spell

((comment) @comment.documentation
  (#match? @comment.documentation "(?s)^/[*][*][^*].*[*]/$"))

; Parameters
(parameter_declaration
  declarator: (identifier) @variable.parameter)

(parameter_declaration
  declarator: (array_declarator) @variable.parameter)

(parameter_declaration
  declarator: (pointer_declarator) @variable.parameter)

; K&R functions
; To enable support for K&R functions,
; add the following lines to your own query config and uncomment them.
; They are commented out as they'll conflict with C++
; Note that you'll need to have `; extends` at the top of your query file.
;
; (parameter_list (identifier) @variable.parameter)
;
; (function_definition
;   declarator: _
;   (declaration
;     declarator: (identifier) @variable.parameter))
;
; (function_definition
;   declarator: _
;   (declaration
;     declarator: (array_declarator) @variable.parameter))
;
; (function_definition
;   declarator: _
;   (declaration
;     declarator: (pointer_declarator) @variable.parameter))
(preproc_params
  (identifier) @variable.parameter)

[
  "__attribute__"
  "__declspec"
  "__based"
  "__cdecl"
  "__clrcall"
  "__stdcall"
  "__fastcall"
  "__thiscall"
  "__vectorcall"
  (ms_pointer_modifier)
  (attribute_declaration)
] @attribute


[
  "soa"
  "task"
  "launch"
  "unmasked"
  "template"
  "typename"
  (sync_expression)
] @keyword

[
  "in"
  "new"
  "delete"
] @keyword.operator

[
  "cdo"
  "cfor"
  "cwhile"
  "foreach"
  "foreach_tiled"
  "foreach_active"
  "foreach_unique"
] @keyword.repeat

"cif" @keyword.conditional

[
  "varying"
  "uniform"
] @keyword.modifier

"__regcall" @attribute

(overload_declarator
  name: _ @function)

(foreach_statement
  range_operator: _ @operator)

(short_vector
  [
    "<"
    ">"
  ] @punctuation.bracket)

(soa_qualifier
  [
    "<"
    ">"
  ] @punctuation.bracket)

(template_argument_list
  [
    "<"
    ">"
  ] @punctuation.bracket)

(template_parameter_list
  [
    "<"
    ">"
  ] @punctuation.bracket)

(llvm_identifier) @function.builtin

; built-in variables
((identifier) @variable.builtin
  (#any-of? @variable.builtin
    "programCount" "programIndex" "taskCount" "taskCount0" "taskCount1" "taskCount2" "taskIndex"
    "taskIndex0" "taskIndex1" "taskIndex2" "threadCount" "threadIndex"))

; preprocessor constants
((identifier) @constant.builtin
  (#any-of? @constant.builtin
    "ISPC" "ISPC_FP16_SUPPORTED" "ISPC_FP64_SUPPORTED" "ISPC_LLVM_INTRINSICS_ENABLED"
    "ISPC_MAJOR_VERSION" "ISPC_MINOR_VERSION" "ISPC_POINTER_SIZE" "ISPC_TARGET_AVX"
    "ISPC_TARGET_AVX2" "ISPC_TARGET_AVX512KNL" "ISPC_TARGET_AVX512SKX" "ISPC_TARGET_AVX512SPR"
    "ISPC_TARGET_NEON" "ISPC_TARGET_SSE2" "ISPC_TARGET_SSE4" "ISPC_UINT_IS_DEFINED" "PI"
    "TARGET_ELEMENT_WIDTH" "TARGET_WIDTH"))

; standard library built-in
((type_identifier) @type.builtin
  (#match? @type.builtin "^RNGState"))

(call_expression
  function: (identifier) @function.builtin
  (#any-of? @function.builtin
    "abs" "acos" "all" "alloca" "and" "any" "aos_to_soa2" "aos_to_soa3" "aos_to_soa4" "asin"
    "assert" "assume" "atan" "atan2" "atomic_add_global" "atomic_add_local" "atomic_and_global"
    "atomic_and_local" "atomic_compare_exchange_global" "atomic_compare_exchange_local"
    "atomic_max_global" "atomic_max_local" "atomic_min_global" "atomic_min_local" "atomic_or_global"
    "atomic_or_local" "atomic_subtract_global" "atomic_subtract_local" "atomic_swap_global"
    "atomic_swap_local" "atomic_xor_global" "atomic_xor_local" "avg_down" "avg_up" "broadcast"
    "ceil" "clamp" "clock" "cos" "count_leading_zeros" "count_trailing_zeros" "doublebits"
    "exclusive_scan_add" "exclusive_scan_and" "exclusive_scan_or" "exp" "extract" "fastmath"
    "float16bits" "floatbits" "float_to_half" "float_to_half_fast" "float_to_srgb8" "floor"
    "frandom" "frexp" "half_to_float" "half_to_float_fast" "insert" "intbits" "invoke_sycl" "isnan"
    "ISPCAlloc" "ISPCLaunch" "ISPCSync" "lanemask" "ldexp" "log" "max" "memcpy" "memcpy64" "memmove"
    "memmove64" "memory_barrier" "memset" "memset64" "min" "none" "num_cores" "or"
    "packed_load_active" "packed_store_active" "packed_store_active2" "packmask" "popcnt" "pow"
    "prefetch_l1" "prefetch_l2" "prefetch_l3" "prefetch_nt" "prefetchw_l1" "prefetchw_l2"
    "prefetchw_l3" "print" "random" "rcp" "rcp_fast" "rdrand" "reduce_add" "reduce_equal"
    "reduce_max" "reduce_min" "rotate" "round" "rsqrt" "rsqrt_fast" "saturating_add"
    "saturating_div" "saturating_mul" "saturating_sub" "seed_rng" "select" "shift" "shuffle"
    "signbits" "sign_extend" "sin" "sincos" "soa_to_aos2" "soa_to_aos3" "soa_to_aos4" "sqrt"
    "streaming_load" "streaming_load_uniform" "streaming_store" "tan" "trunc"))
