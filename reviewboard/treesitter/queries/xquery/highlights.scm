
; TODO: maybe for builtins (atomic_or_union_type
; ; [
  ; ((identifier) @type.name .)
  ; ((identifier) @namespace.local (#not-eq? @namespace.local  "xs") . ":" . (identifier) @type.local_name )
  ; ]
; (atomic_or_union_type .
;   (identifier) @namespace.builtin (#eq? @namespace.builtin  "xs") . ":" .
;   (identifier) @type.builtin.atomic (#any-of? @type.builtin.atomic
;   "anyAtomicType" "untypedAtomic" "dateTime" "dateTimeStamp" "time" "date" "duration" "yearMonthDuration" "dayTimeDuration" "float" "double" "decimal" "integer" "nonPositiveInteger" "negativeInteger" "long" "int" "short" "byte" "nonNegativeInteger" "unsignedLong" "unsignedInt" "unsignedShort" "unsignedByte" "positiveInteger" "gYearMonth" "gYear" "gMonthDay" "gDay" "gMonth" "string" "normalizedString" "token" "language" "NMTOKEN" "Name" "NCName" "ID" "IDREF" "ENTITY" "boolean" "base64Binary" "hexBinary" "anyURI" "QName" "NOTATION"
;   ))
; 2.5.4 SequenceType Syntax
(type_declaration  "as" @keyword) @type.declaration
(parenthesized_item_type . "(" ")" ) @type.parenthesized_item
(sequence_type "empty-sequence" "(" ")" ) @type.empty_sequence
(atomic_or_union_type) @type.atomic_or_union
(name_test) @type.name_test
 kind_test: (_) @type.kind_test
 (any_item) @type.any_test
 func_test: (_) @type.func_test
(occurrence_indicator) @symbol.occurrence_indicator
(wildcard) @type.wildcard
; 3.1 Primary Expressions
; 3.1.1 Literals
(string_literal [ "'" "\""] @punctuation.bracket.string )
[(char_data) (string_constructor_chars) ] @string
[ (escape_quote) (escape_apos) (escape_enclosed) (char_ref) (predefined_entity_ref) ] @string.special
; numbers
[(integer_literal) (decimal_literal) (double_literal)] @number
; 3.1.2 Variable References
(var_ref) @variable.reference
;3.1.3 Parenthesized Expressions
(parenthesized_expr [ "(" ")" ] @punctuation.bracket.paren_expr)
;3.1.4 Context Item Expression
(context_item_expr) @operator.context
;3.1.5 Static Function Calls
; A.3 Reserved Function Names
(function_call .
  [
  ncname: (identifier) @function.call (#not-any-of? @function.call  "array" "attribute" "comment" "document-node" "element" "empty-sequence" "function" "if" "item" "map" "namespace-node" "node" "processing-instruction" "schema-attribute" "schema-element" "switch" "text" "typeswitch")
  prefixed: (identifier)
  (uri_qualified_name) @function.call.URIQualifiedName
  ]
  ( ":" @punctuation.delimiter.QName  .
   local: (identifier) @function.call
   )*
  (arg_list) @function.call
)
(arg_list arg: (placeholder) @parameter.placeholder)
; 3.2.2 Dynamic Function Calls
; 3.1.6 Named Function References
(named_function_ref "#" @punctuation.delimiter . (integer_literal) ) @function.named_function_ref
; 3.1.7 Inline Function Expressions
(inline_function_expr
  ((annotation) @function.annotation)?
  "function"
  "(" @punctuation.bracket.params
  (param_list)*
  ")" @punctuation.bracket.params
  ) @function.inline
; 3.1.8 Enclosed Expressions
(enclosed_expr  [ "{" "}" ] @punctuation.bracket.enclosed_expr)
; 3.2 Postfix Expressions
(arg_list [ "(" ")" ] @punctuation.bracket.arg_list )
(predicate [ "[" "]" ] @punctuation.bracket.predicate)
; 3.11.3.2 Postfix Lookup
(postfix_lookup "?" @operator.postfix_lookup key: (_) @constant.key_specifier)
; 3.3 Path Expressions
[ "/" "//" ] @operator.path
axis: (_) @constant.axis_step
; 3.4 Sequence Expressions
; 3.4.1 Constructing Sequences
;@see parenthesized_expr
(range_expr [ "to" ] @operator.range)
;3.4.2 Combining Node Sequences
(union_expr [ "union" "|" ] @operator.union );
(intersect_except_expr [ "intersect" "except"] @operator.intersect_except)
;3.5 Arithmetic Expressions
(additive_expr [ "-" "+"] @operator.additive)
(multiplicative_expr [ "*" "div" "idiv" "mod"] @operator.multiplicative )
(unary_expr [ "-" "+"] @operator)
;3.6 String Concatenation Expressions
(string_concat_expr ["||"] @operator.concat )
;3.7 Comparison Expressions
(comparison_expr [ "eq" "ne" "lt" "le" "gt" "ge" "is"  "=" "!=" "<" "<=" ">" ">="  "<<" ">>" ] @operator.comparison)
; 3.8 Logical Expressions
(and_expr [ "and" ] @operator.and)
(or_expr [ "or" ] @operator.or)
;3.9.1 Direct Element Constructors: tag tag.attribute tag.delimiter
(start_tag . "<"  @tag.delimiter ">" @tag.delimiter ) @tag.start
(end_tag . "</" @tag.delimiter ">" @tag.delimiter) @tag.end
(empty_tag . "<" @tag.delimiter "/>" @tag.delimiter) @tag.empty
(direct_attribute "=" @operator.assignment.attr) @tag.attribute
(attribute_value ["'" "\"" ] @punctuation.bracket)
; 3.9.3 Computed Constructors
computed_constructor: (_ .
  [ "element" "attribute" "document" "text" "processing-instruction"
    "comment" "namespace" ] @keyword.computed_constructor ) @constructor.node
; 3.10 String Constructors
(string_constructor . "``[" "]``" ) @constructor.string
(interpolation . "`{" "}`" ) @constructor.interpolation
; 3.11 Maps and Arrays
(map_constructor "map" "{" "}" ) @function.constructor.map
(map_entry ":" @punctuation.delimiter.map )
(square_array_constructor "[" "]" ) @function.constructor.array
(curly_array_constructor "array" (enclosed_expr)) @function.constructor.array
; 3.11.3 The Lookup Operator ("?") for Maps and Arrays
; Unary lookup is used in predicates (e.g. $map[?name='Mike'] or with the simple map operator
;3.11.3.1 Unary Lookup
(unary_lookup "?"  @operator.lookup.unary key: (_) @constant.key_specifier)
; 3.12 FLWOR Expressions TODO
(tumbling_window_clause . "for" "tumbling" "window" "in" ) @keyword.tumbling_window_clause
(sliding_window_clause . "for" "sliding" "window" "in" )  @keyword.sliding_window_clause
(window_start_condition "start" "at""previous" "next" "when"  @keyword.window_start_condition )
(window_end_condition "end" "at" "previous" "next" "when" @keyword.window_end_condition)
 (_
   [
   current_item: (variable) @variable.current
   positional_variable: (variable) @variable.positional
   previous_item: (variable) @variable.previous
   next_item: (variable) @variable.next
   ]
   )
(for_clause . "for") @keyword.for_clause
(for_binding (["allowing" "empty" "at" "in" ] @keyword.for_binding)*) @variable.for_binding
(let_clause . "let" ) @keyword.let_clause
(let_binding) @variable.let_binding
[ (count_clause "count") (where_clause "where")
  (order_by_clause [ "stable" "order" "by" "ascending" "collation" "descending" "empty" "greatest" "least" "collation"] )
  (group_by_clause "group" "by") (grouping_spec)
] @keyword.flwor.intermediate
(return_clause "return" @keyword.return.flwor)
; 3.13 Ordered and Unordered Expressions
(unordered_expr "unordered") @keyword.unordered_expr
(ordered_expr "ordered") @keyword.ordered_expr
; 3.14 Conditional Expressions
(if_expr "if" "then" "else") @keyword.if_expr
;3.15 Switch Expression
(switch_expr "switch" "default" "return") @keyword.switch_expr
(switch_clause "case" "return" ) @keyword.switch_clause
;3.16 Quantified Expressions
(quantified_expr ["some" "every"] "in") @keyword.quantified_expr
;3.17 Try/Catch Expressions
(try_catch_expr (try_clause "try") (catch_clause "catch")) @keyword.try_catch_expr
;3.18 Expressions on SequenceTypes
;3.18.1 Instance Of
(instance_of_expr) @keyword.instance_of;
;3.18.2 Typeswitch
(typeswitch_expr "typeswitch"  "default" "return" ) @keyword.block.typeswitch
(typeswitch_case_clause "case" "return" ) @keyword.case.typeswitch
;3.18.3 Cast
(cast_expr  "cast"  "as" ) @keyword.block.cast
;3.18.4 Castable
(castable_expr  "castable"  "as") @keyword.block.castable
;3.18.6 Treat
(treat_expr  "treat"  "as"  ) @keyword.block.treat_as
;3.19 Simple map operator (!)
(bang_expr  "!"  @operator.bang )
; 3.20 Arrow operator (=>)
(arrow_expr  "=>"   @operator.arrow )
(arrow_function) @function
; 3.21 Validate Expressions TODO?
; 3.22 Extension Expressions TODO?
;4 Modules and Prologs
;4.1 Version Declaration
(version_declaration ["version" "encoding"] @keyword.version ) @define.version
; 4.2 Module Declaration
(module_declaration) @define.module
; 4.3 Boundary-space Declaration
(boundary_space_declaration "boundary-space" @keyword [ "preserve" "strip"] @keyword) @define.boundary_space
; 4.4 Default Collation Declaratiodefault_collation_declarationn
(default_collation_declaration "default" @keyword "collation" @keyword) @define.default_collation
; 4.5 Base URI Declaration
(base_uri_declaration "base-uri" @keyword ) @define.base_uri
; 4.6 Construction Declaration
(construction_declaration "construction"  @keyword . ["strip" "preserve" ] @keyword) @define.construction
; 4.7 Ordering Mode Declaration
(ordering_mode_declaration "ordering"  @keyword . ["ordered" "unordered"]	@keyword) @define.ordering_mode
; 4.8 Empty Order Declaration
(empty_order_declaration "default" @keyword . "order" @keyword . "empty" @keyword . ["greatest"  "least" ] @keyword) @define.empty_order
; 4.9 Copy-Namespaces Declaration
(copy_namespaces_declaration "copy-namespaces" @keyword . ["preserve"  "no-preserve"] @keyword . ["inherit"  "no-inherit"] @keyword) @define.copy_namespaces
; 4.10 Decimal Format Declaration
(decimal_format_declaration "decimal-format" @keyword.decimal_format) @define.decimal_format
(df_property_define _ @keyword.df_property "=" @operator.df_property)
; 4.11 Schema Import
(schema_import  "schema" @keyword.schema_import ) @include.schema_import
(schema_prefix "default" "element" "namespace" ) @keyword.schema_prefix
; 4.12 Module Import
(module_import "module" @keyword ) @include.module_import.
; 4.13 Namespace Declaration
(namespace_declaration) @define.namespace_declaration
;4.14 Default Namespace Declaration
(default_namespace_declaration "default"  @keyword [ "element"  "function" ] @keyword "namespace" @keyword) @define.default_namespace
; 4.15 Annotations
;4.16 Variable Declaration
(variable_declaration ((annotation) @variable.annotation)? "variable" @keyword) @define.variable
; 4.17 Context Item Declaration
(context_item_declaration "context" @keyword "item" @keyword) @define.context_item
; 4.18 Function Declaration
(function_declaration ((annotation) @function.annotation)? "function" @keyword
                      "(" @punctuation.bracket ")" @punctuation.bracket) @define.function
; 33 ref by:  FunctionDecl InlineFunctionExpr
(param_list) @parameter.param_list
; defaults in EQNames
":" @punctuation.delimiter.QName
prefixed: (identifier) @namespace.QName.prefixed
; assigning values token:  ContextItemDecl VarDecl GroupingSpec LetBinding
":=" @operator.assignment
; ref ContextItemDecl VarDecl FunctionDecl
"external" @import.external
; namespace define pattern in declarations
(_ "namespace"  @keyword (identifier) @namespace "=" @operator.namespace_assignment)
; end of declaration delimiter
(_ ";" @punctuation.delimiter.declaration_separator .)
;4.2 Module Declaration
"," @punctuation.delimiter
(comment) @comment
(ERROR) @error
