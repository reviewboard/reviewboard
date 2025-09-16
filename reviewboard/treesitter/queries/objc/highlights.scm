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


; Preprocs
(preproc_undef
  name: (_) @constant) @keyword.directive

; Includes
(module_import
  "@import" @keyword.import
  path: (identifier) @module)

((preproc_include
  _ @keyword.import
  path: (_))
  (#any-of? @keyword.import "#include" "#import"))

; Type Qualifiers
[
  "@optional"
  "@required"
  "__covariant"
  "__contravariant"
  (visibility_specification)
] @keyword.modifier

; Storageclasses
[
  "@autoreleasepool"
  "@synthesize"
  "@dynamic"
  "volatile"
  (protocol_qualifier)
] @keyword.modifier

; Keywords
[
  "@protocol"
  "@interface"
  "@implementation"
  "@compatibility_alias"
  "@property"
  "@selector"
  "@defs"
  "availability"
  "@end"
] @keyword

(class_declaration
  "@" @keyword.type
  "class" @keyword.type) ; I hate Obj-C for allowing "@ class" :)

(method_definition
  [
    "+"
    "-"
  ] @keyword.function)

(method_declaration
  [
    "+"
    "-"
  ] @keyword.function)

[
  "__typeof__"
  "__typeof"
  "typeof"
  "in"
] @keyword.operator

[
  "@synchronized"
  "oneway"
] @keyword.coroutine

; Exceptions
[
  "@try"
  "__try"
  "@catch"
  "__catch"
  "@finally"
  "__finally"
  "@throw"
] @keyword.exception

; Variables
((identifier) @variable.builtin
  (#any-of? @variable.builtin "self" "super"))

; Functions & Methods
[
  "objc_bridge_related"
  "@available"
  "__builtin_available"
  "va_arg"
  "asm"
] @function.builtin

(method_definition
  (identifier) @function.method)

(method_declaration
  (identifier) @function.method)

(method_identifier
  (identifier)? @function.method
  ":" @function.method
  (identifier)? @function.method)

(message_expression
  method: (identifier) @function.method.call)

; Constructors
((message_expression
  method: (identifier) @constructor)
  (#eq? @constructor "init"))

; Attributes
(availability_attribute_specifier
  [
    "CF_FORMAT_FUNCTION"
    "NS_AVAILABLE"
    "__IOS_AVAILABLE"
    "NS_AVAILABLE_IOS"
    "API_AVAILABLE"
    "API_UNAVAILABLE"
    "API_DEPRECATED"
    "NS_ENUM_AVAILABLE_IOS"
    "NS_DEPRECATED_IOS"
    "NS_ENUM_DEPRECATED_IOS"
    "NS_FORMAT_FUNCTION"
    "DEPRECATED_MSG_ATTRIBUTE"
    "__deprecated_msg"
    "__deprecated_enum_msg"
    "NS_SWIFT_NAME"
    "NS_SWIFT_UNAVAILABLE"
    "NS_EXTENSION_UNAVAILABLE_IOS"
    "NS_CLASS_AVAILABLE_IOS"
    "NS_CLASS_DEPRECATED_IOS"
    "__OSX_AVAILABLE_STARTING"
    "NS_ROOT_CLASS"
    "NS_UNAVAILABLE"
    "NS_REQUIRES_NIL_TERMINATION"
    "CF_RETURNS_RETAINED"
    "CF_RETURNS_NOT_RETAINED"
    "DEPRECATED_ATTRIBUTE"
    "UI_APPEARANCE_SELECTOR"
    "UNAVAILABLE_ATTRIBUTE"
  ]) @attribute

; Macros
(type_qualifier
  [
    "_Complex"
    "_Nonnull"
    "_Nullable"
    "_Nullable_result"
    "_Null_unspecified"
    "__autoreleasing"
    "__block"
    "__bridge"
    "__bridge_retained"
    "__bridge_transfer"
    "__complex"
    "__kindof"
    "__nonnull"
    "__nullable"
    "__ptrauth_objc_class_ro"
    "__ptrauth_objc_isa_pointer"
    "__ptrauth_objc_super_pointer"
    "__strong"
    "__thread"
    "__unsafe_unretained"
    "__unused"
    "__weak"
  ]) @function.macro

[
  "__real"
  "__imag"
] @function.macro

((call_expression
  function: (identifier) @function.macro)
  (#eq? @function.macro "testassert"))

; Types
(class_declaration
  (identifier) @type)

(class_interface
  "@interface"
  .
  (identifier) @type
  superclass: _? @type
  category: _? @module)

(class_implementation
  "@implementation"
  .
  (identifier) @type
  superclass: _? @type
  category: _? @module)

(protocol_forward_declaration
  (identifier) @type) ; @interface :(

(protocol_reference_list
  (identifier) @type) ; ^

[
  "BOOL"
  "IMP"
  "SEL"
  "Class"
  "id"
] @type.builtin

; Constants
(property_attribute
  (identifier) @constant
  "="?)

[
  "__asm"
  "__asm__"
] @constant.macro

; Properties
(property_implementation
  "@synthesize"
  (identifier) @variable.member)

((identifier) @variable.member
  (#has-ancestor? @variable.member struct_declaration))

; Parameters
(method_parameter
  ":" @function.method
  (identifier) @variable.parameter)

(method_parameter
  declarator: (identifier) @variable.parameter)

(parameter_declaration
  declarator: (function_declarator
    declarator: (parenthesized_declarator
      (block_pointer_declarator
        declarator: (identifier) @variable.parameter))))

"..." @variable.parameter.builtin

; Operators
"^" @operator

; Literals
(platform) @string.special

(version_number) @string.special

; Punctuation
"@" @punctuation.special

[
  "<"
  ">"
] @punctuation.bracket
