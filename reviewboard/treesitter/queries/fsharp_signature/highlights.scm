;; Highlights for the fsharp_signature grammar (.fsi files).
;; Derived from queries/highlights.scm, restricted to nodes the signature
;; grammar actually produces (it narrows the expression layer and declares
;; its own supertypes, so `_type`/`_pattern`/expression nodes are absent).

;; ----------------------------------------------------------------------------
;; Literals and comments

;; `@spell` first: the colour capture, listed last, is the one that wins.
[
  (line_comment)
  (xml_doc)
  (block_comment)
] @spell @comment

(xml_doc) @spell @comment.documentation

(const
  [
   (_) @constant
   (unit) @constant.builtin
  ])

(primary_constr_args (_) @variable.parameter)

(class_as_reference
  (_) @variable.parameter.builtin)

((argument_patterns (long_identifier (identifier) @character.special))
 (#match? @character.special "^_"))

;; ----------------------------------------------------------------------------
;; Types

(type_name type_name: (_) @type.definition)
(exception_definition exception_name: (_) @type.definition)

[
 (atomic_type)
 (simple_type)
 (generic_type)
 (function_type)
 (compound_type)
 (postfix_type)
 (list_type)
 (static_type)
 (constrained_type)
 (flexible_type)
 (byref_type)
 (paren_type)
 (struct_type)
] @type

(member_signature
  .
  (identifier) @function.member)

(member_signature
  (curried_spec
    (arguments_spec
      "*"* @operator
      (argument_spec
        (argument_name_spec
          "?"? @character.special
          name: (_) @variable.parameter)))))

(union_type_case (identifier) @constant)

(wildcard_pattern) @character.special

(identifier_pattern
  .
  (_) @constant
  .
  (_) @variable)

(optional_pattern
  "?" @character.special)

(fsi_directive_decl . (string) @module)

(import_decl . (_) @module)
(named_module
  name: (_) @module)
(namespace
  name: (_) @module)
(module_defn
  .
  (_) @module)

(record_fields
  (record_field
    .
    (identifier) @property))

(value_declaration_left . (_) @variable)

(function_declaration_left
  . (_) @function)

(argument_patterns) @variable.parameter
(typed_pattern
  . (_) @variable.parameter)

(member_defn
  (method_or_prop_defn
    (property_or_ident . (identifier) @function .)
    args: (_)* @variable.parameter))

(member_defn
  (method_or_prop_defn
    (property_or_ident
      instance: (identifier) @variable.parameter.builtin
      method: (identifier) @function.method)
    args: (_)* @variable.parameter))

[
  (xint)
  (int)
  (int16)
  (uint16)
  (int32)
  (uint32)
  (int64)
  (uint64)
  (nativeint)
  (unativeint)
] @number

[
  (ieee32)
  (ieee64)
  (float)
  (decimal)
] @number.float

(bool) @boolean

([
  (string)
  (triple_quoted_string)
  (verbatim_string)
  (char)
  (format_string)
  (format_triple_quoted_string)
] @spell @string)

(compiler_directive_decl) @keyword.directive

(preproc_line
  "#line" @keyword.directive)

(attribute
  target: (identifier)? @keyword
  (simple_type) @attribute)

[
  "("
  ")"
  "{"
  "}"
  "["
  "]"
  "[|"
  "|]"
  "{|"
  "|}"
] @punctuation.bracket

[
  "[<"
  ">]"
] @punctuation.special

[
  ","
  ":"
  "."
] @punctuation.delimiter

[
  "|"
  "="
  "->"
  "*"
  (op_identifier)
] @operator

(generic_type
  [
   "<"
   ">"
  ] @punctuation.bracket)

[
  "when"
  "then"
] @keyword.conditional

[
  "and"
  "or"
  "not"
] @keyword.operator

[
  "open"
  "#r"
  "#load"
] @keyword.import

[
  "abstract"
  "delegate"
  "extern"
  "static"
  "inline"
  "mutable"
  "override"
  "rec"
  "global"
  (access_modifier)
] @keyword.modifier

[
  "let"
  "member"
] @keyword.function

[
  "enum"
  "type"
  "exception"
  "inherit"
  "interface"
  "and"
  "class"
  "struct"
] @keyword.type

[
  "as"
  "begin"
  "end"
  "default"
  "do"
  "get"
  "set"
  "new"
  "of"
  "struct"
  "val"
  "module"
  "namespace"
  "with"
] @keyword

[
  "null"
] @constant.builtin


(preproc_if
  [
    "#if" @keyword.directive
    "#endif" @keyword.directive
  ]
  condition: (_)? @keyword.directive)

(preproc_else
  "#else" @keyword.directive)

(preproc_inactive) @comment

((long_identifier
  (identifier)+ @variable.member
  .
  (identifier)))

;; Every segment of a module path (`namespace Company.Product`,
;; `open System.IO`), a type path or an attribute path is part of that name,
;; not a member access; re-capture the segments the rule above marked as
;; members (the last capture of a node wins). @type.builtin follows so it
;; still wins over the plain @type.
(namespace name: (long_identifier (identifier) @module))
(named_module name: (long_identifier (identifier) @module))
(import_decl (long_identifier (identifier) @module))
(module_abbrev (long_identifier (identifier) @module))
(simple_type (long_identifier (identifier) @type))
(attribute (simple_type (long_identifier (identifier) @attribute)))

((simple_type
   (long_identifier
     (identifier) @type.builtin))
 (#any-of? @type.builtin "bool" "byte" "sbyte" "int16" "uint16" "int" "uint" "int64" "uint64" "nativeint" "unativeint" "decimal" "float" "double" "float32" "single" "char" "string" "unit"))

((identifier) @module.builtin
 (#any-of? @module.builtin "Array" "Async" "Directory" "File" "List" "Option" "Path" "Map" "Set" "Lazy" "Seq" "Task" "String" "Result" ))
