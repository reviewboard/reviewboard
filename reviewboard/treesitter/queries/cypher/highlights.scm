(comment) @comment

(string_literal) @string
(escaped_char) @string.escape
(number_literal) @number
(boolean_literal) @boolean
"null" @constant

[
 "[" "]"
 "{" "}"
 "(" ")"
] @punctuation.bracket

[
 ","
 "."
 ":"
 ";"
] @punctuation.delimiter

[
 "or"
 "xor"
 "and"
 "not"
 "="
 "<>"
 "<"
 ">"
 "<="
 ">="
 "-"
 "+"
 "*"
 "/"
 "%"
 "^"
] @operator

[
 "all"
 "asc"
 "ascending"
 "by"
 "create"
 "delete"
 "desc"
 "descending"
 "detach"
 "exists"
 "limit"
 "match"
 "merge"
 "on"
 "optional"
 "order"
 "remove"
 "set"
 "skip"
 "where"
 "with"
 "union"
 "unwind"
 "as"
 "contains"
 "distinct"
 "ends"
 "in"
 "is"
 "starts"
 "constraint"
 "unique"
 "case"
 "when"
 "then"
 "else"
 "end"
 "mandatory"
 "scalar"
 "of"
 "add"
 "drop"
] @keyword

"return" @keyword.return

(node_pattern) @constant
(relationship_pattern) @constant
(variable) @type
