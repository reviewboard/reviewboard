[
 "do"
] @keyword

[
 "debug"
] @keyword.directive

[
 "ignore"
] @keyword.control

"return" @keyword.control.return

"null" @keyword.constant

[
 "if"
 "else"
 "switch"
 "case"
] @keyword.control.conditional

[
 "and"
 "or"
 "in"
 "with"
 "not"
 "from_candid"
 "to_candid"
 "debug_show"
 "implies"
] @keyword.operator

[
 "label"
 "for"
 "loop"
 "while"
 "break"
 "continue"
] @keyword.control.repeat

[
 "try"
 "catch"
 "finally"
 "throw"
 "assert"
] @keyword.control.exception

[
 "true" "false"
] @constant.builtin.boolean

[
 "import"
] @keyword.control.import

[
 "private"
 "public"
 "query"
 "shared"
 "async"
 "async*"
 "await"
 "await*"
 "stable"
 "flexible"
 "system"
 "invariant"
] @keyword.storage.modifier

[
 "let"    "class" "func"
 "type"   "actor" "object"
 "module"
] @keyword.storage.type

(dec_var "var" @keyword.storage.type)

"var" @keyword.storage.modifier

"prim" @keyword.directive

op: [
 "="   "|>"  "+"    "-"   "*"   "/"  "%"   "+%"  "-%"   "*%"   "|"
 "&"   "^"   "#"    "**"  "**%" "==" "!="  " > " " < "  "<="   ">="
 "<<"  " >>" "<<>"  "<>>" "+="  "-=" "*="  "/="  "%="   "**-"  "+%="
 "-%=" "*%=" "**%=" "&="  "|="  "^=" "<<=" ">>=" "<<>=" "<>>=" "@="
] @operator

unary: "!" @keyword.control

(do_exp
 "?" @keyword.control
)

unary: "?" @operator

(typ_empty_variant
 [
  "{" "#" "}"
 ] @type.enum.variant
)

[
 "#" "<:"
] @punctuation.special

(nat) @constant.numeric.integer

(float) @constant.numeric.float

(line_comment) @comment.line

(block_comment) @comment.block

(doc_comment) @comment.block.documentation

(typ_id
 type_name: (name) @type.builtin
 (#any-of? @type.builtin 
  "Bool"      "Char"  "Text"
  "Float"     "Int"   "Int8"
  "Int16"     "Int32" "Int64"
  "Nat"       "Nat8"  "Nat16"
  "Nat32"     "Nat64" "Blob"
  "Principal" "Error" "Region"
 )
)

(imp
 module_pattern: [
  (variable
   variable_name: (name) @namespace
  )
  (pat_bin
   (variable
    variable_name: (name) @namespace
   )
  )
 ]?
 module_path: (text) @string.special.path
)
 
(placeholder) @constant.builtin

(char (escape) @constant.character.escape)

(char) @constant.character

(text (escape) @constant.character.escape)

(text) @string

(call_exp
 invoked_value: (exp_post
  (member
   key: (name) @function
  )
  .
 )
)

(call_exp
 invoked_value: (variable
  variable_name: (name) @function
 )
)

(exp_post
 .
 (_
  indexed_value: (variable
   variable_name: (name) @namespace
  )
 )
)

(member
 key: (name) @variable.other.member
)

(typ_component
 component_name: (name) @type
)

(_
 variant_name: (name) @type.enum.variant
)

(_
 field_name: (name) @variable.other.member
)

(_
 function_name: (name) @function
)

(_
 module_name: (name) @namespace
)

(_
 class_name: (name) @namespace
)

(_
 object_name: (name) @namespace
)

(_
 label_name: (name) @label
)

(_
 type_parameter_name: (name) @type.parameter
)

(_
 type_name: (name) @type
)

(_
 parameter_name: (name) @variable.parameter
)

(_
 variable_name: (name) @variable
)

(typ_item
 tuple_component_name: (name) @comment.block.documentation
)

[
  ":" ";" "," "."
] @punctuation.delimiter

[
 "[" "]" "{" "}"
 "(" ")" "<" ">"
] @punctuation.bracket

