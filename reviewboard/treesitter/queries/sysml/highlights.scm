; Keywords - Definitions
[
  "def"
  "package"
  "library"
  "standard"
  "part"
  "item"
  "port"
  "action"
  "state"
  "constraint"
  "requirement"
  "attribute"
  "enum"
  "connection"
  "interface"
  "allocation"
  "metadata"
  "flow"
  "use"
  "case"
  "calc"
  "analysis"
  "verification"
  "concern"
  "stakeholder"
  "view"
  "viewpoint"
  "rendering"
  "render"
  "occurrence"
  "individual"
  "snapshot"
  "timeslice"
  "event"
  "variation"
  "variant"
] @keyword

; Keywords - Modifiers
[
  "abstract"
  "ref"
  "ordered"
  "derived"
  "constant"
] @keyword.modifier

; Node-based modifiers
(nonunique_modifier) @keyword.modifier

; Keywords - Visibility
[
  "public"
  "private"
  "protected"
] @keyword.modifier

; Keywords - Direction
[
  "in"
  "out"
  "inout"
] @keyword.modifier

; Keywords - Imports and Aliases
[
  "import"
  "alias"
  "for"
  "from"
  "all"
] @keyword.import

; Keywords - Relationships
[
  "specializes"
  "redefines"
  "subsets"
  "references"
  "about"
] @keyword

; Keywords - Behavioral
[
  "entry"
  "do"
  "exit"
  "transition"
  "accept"
  "send"
  "via"
  "after"
  "at"
  "when"
  "first"
  "then"
  "loop"
  "until"
  "parallel"
  "decide"
  "merge"
  "fork"
  "join"
  "done"
  "perform"
  "terminate"
  "assign"
  "succession"
  "message"
] @keyword

; Keywords - Control Flow
[
  "if"
  "else"
  "while"
  "return"
] @keyword.control

; Keywords - Requirements
[
  "subject"
  "actor"
  "objective"
  "frame"
  "require"
  "assume"
  "assert"
  "satisfy"
  "verify"
] @keyword

; Keywords - Connections
[
  "connect"
  "bind"
  "allocate"
  "end"
  "to"
] @keyword

; Keywords - Views
[
  "expose"
  "filter"
  "include"
] @keyword

; Keywords - Other
[
  "dependency"
  "doc"
  "comment"
  "locale"
  "default"
  "of"
  "by"
  "new"
  "meta"
  "exhibit"
  "language"
  "rep"
  "crosses"
  "defined"
  "stream"
] @keyword

; Type testing operators
[
  "istype"
  "hastype"
] @keyword.operator

; Logical Operators
[
  "and"
  "or"
  "xor"
  "implies"
  "not"
] @keyword.operator

; Operators - Relationships
[
  ":>"
  ":>>"
  "::>"
] @operator

; Operators - Typing
[
  ":"
  "::"
] @operator

; Operators - Assignment
[
  "="
  ":="
] @operator

; Operators - Arithmetic
[
  "+"
  "-"
  "*"
  "/"
  "%"
  "**"
] @operator

; Operators - Comparison
[
  "=="
  "!="
  "<"
  ">"
  "<="
  ">="
] @operator

; Operators - Other
[
  "~"
  "??"
  "."
  "->"
  ".?"
  "&"
  "|"
  ".."
] @operator

; Punctuation - Brackets
[
  "{"
  "}"
] @punctuation.bracket

[
  "["
  "]"
] @punctuation.bracket

[
  "("
  ")"
] @punctuation.bracket

; Punctuation - Delimiters
[
  ";"
  ","
] @punctuation.delimiter

; Punctuation - Special
[
  "#"
  "@"
] @punctuation.special

; Literals
(integer_literal) @number
(real_literal) @number.float
(string_literal) @string
(boolean_literal) @boolean
(null_literal) @constant.builtin

; Names - Default
(identifier) @variable

; Definitions - Type names
(part_definition
  (identification (name (identifier) @type.definition)))
(item_definition
  (identification (name (identifier) @type.definition)))
(port_definition
  (identification (name (identifier) @type.definition)))
(action_definition
  (identification (name (identifier) @type.definition)))
(state_definition
  (identification (name (identifier) @type.definition)))
(constraint_definition
  (identification (name (identifier) @type.definition)))
(requirement_definition
  (identification (name (identifier) @type.definition)))
(attribute_definition
  (identification (name (identifier) @type.definition)))
(enumeration_definition
  (identification (name (identifier) @type.definition)))
(connection_definition
  (identification (name (identifier) @type.definition)))
(interface_definition
  (identification (name (identifier) @type.definition)))
(allocation_definition
  (identification (name (identifier) @type.definition)))
(flow_definition
  (identification (name (identifier) @type.definition)))
(use_case_definition
  (identification (name (identifier) @type.definition)))
(calc_definition
  (identification (name (identifier) @type.definition)))
(analysis_definition
  (identification (name (identifier) @type.definition)))
(verification_definition
  (identification (name (identifier) @type.definition)))
(concern_definition
  (identification (name (identifier) @type.definition)))
(viewpoint_definition
  (identification (name (identifier) @type.definition)))
(view_definition
  (identification (name (identifier) @type.definition)))
(rendering_definition
  (identification (name (identifier) @type.definition)))
(occurrence_definition
  (identification (name (identifier) @type.definition)))
(individual_definition
  (identification (name (identifier) @type.definition)))
(metadata_definition
  (identification (name (identifier) @type.definition)))
(case_definition
  (identification (name (identifier) @type.definition)))
(generic_definition
  (identification (name (identifier) @type.definition)))

; Usages - Instance/field names
(part_usage
  (usage_declaration (identification (name (identifier) @variable))))
(item_usage
  (usage_declaration (identification (name (identifier) @variable))))
(port_usage
  (usage_declaration (identification (name (identifier) @variable))))
(attribute_usage
  (usage_declaration (identification (name (identifier) @variable))))
(connection_usage
  (usage_declaration (identification (name (identifier) @variable))))
(interface_usage
  (usage_declaration (identification (name (identifier) @variable))))
(allocation_usage
  (usage_declaration (identification (name (identifier) @variable))))
(flow_usage
  (usage_declaration (identification (name (identifier) @variable))))
(state_usage
  (usage_declaration (identification (name (identifier) @type))))
(constraint_usage
  (usage_declaration (identification (name (identifier) @type))))
(requirement_usage
  (usage_declaration (identification (name (identifier) @type))))
(occurrence_usage
  (usage_declaration (identification (name (identifier) @type))))
(individual_usage
  (usage_declaration (identification (name (identifier) @type))))
(view_usage
  (usage_declaration (identification (name (identifier) @type))))
(rendering_usage
  (usage_declaration (identification (name (identifier) @type))))
(concern_usage
  (usage_declaration (identification (name (identifier) @type))))
(viewpoint_usage
  (usage_declaration (identification (name (identifier) @type))))
(enumeration_usage
  (usage_declaration (identification (name (identifier) @type))))
(timeslice_usage
  (usage_declaration (identification (name (identifier) @type))))
(snapshot_usage
  (usage_declaration (identification (name (identifier) @type))))
(event_occurrence_usage
  (usage_declaration (identification (name (identifier) @type))))
(variation_usage
  (usage_declaration (identification (name (identifier) @type))))
(variant_usage
  (usage_declaration (identification (name (identifier) @type))))
(actor_usage
  (usage_declaration (identification (name (identifier) @type))))
(stakeholder_usage
  (usage_declaration (identification (name (identifier) @type))))
(objective_usage
  (usage_declaration (identification (name (identifier) @type))))
(exhibit_usage
  (usage_declaration (identification (name (identifier) @type))))
(reference_usage
  (usage_declaration (identification (name (identifier) @variable))))
(parameter_usage
  (usage_declaration (identification (name (identifier) @variable))))
(generic_usage
  (usage_declaration (identification (name (identifier) @variable))))
(metadata_usage
  (identification (name (identifier) @variable)))
(end_usage
  (usage_declaration (identification (name (identifier) @variable))))
(end_usage
  (identification (name (identifier) @variable)))
(feature_usage
  (identification (name (identifier) @variable)))

; Usages - Behavioral names (function-like)
(action_usage
  (usage_declaration (identification (name (identifier) @function))))
(calc_usage
  (usage_declaration (identification (name (identifier) @function))))
(use_case_usage
  (usage_declaration (identification (name (identifier) @function))))
(case_usage
  (usage_declaration (identification (name (identifier) @function))))
(analysis_usage
  (usage_declaration (identification (name (identifier) @function))))
(verification_usage
  (usage_declaration (identification (name (identifier) @function))))

; Type references
(typing_part (qualified_name (name (identifier) @type)))
(definition_specialization (qualified_name (name (identifier) @type)))
(specialization_part (qualified_name (name (identifier) @type)))

; Expression highlighting
(function_call_expression (qualified_name (name (identifier) @function.call)))
(new_expression "new" @keyword.operator)
(cast_expression "as" @keyword.operator)
(metadata_access_expression "@" @punctuation.special)
(conditional_expression "?" @operator)
(select_expression ".?" @operator)

; Package names
(package_definition
  (identification (name (identifier) @namespace)))
(library_package
  (identification (name (identifier) @namespace)))

; Statements - Names as labels (target state/action references)
(if_then_statement (name (identifier) @label))
(first_statement (name (identifier) @label))
(else_statement (name (identifier) @label))
(transition_statement (name (identifier) @label))

; Statements - Identification children
(alias_statement
  (identification (name (identifier) @variable)))
(flow_statement
  (identification (name (identifier) @variable)))
(assert_statement
  (identification (name (identifier) @variable)))
(assume_statement
  (identification (name (identifier) @variable)))
(succession_statement
  (identification (name (identifier) @variable)))
(message_statement (name (identifier) @variable))
(stream_statement (name (identifier) @variable))
(textual_representation
  (identification (name (identifier) @variable)))

; Expressions - Invocation
(invocation_expression (name (identifier) @function.call))

; Shorthand attributes
(shorthand_attribute (name (identifier) @variable))

; Prefix metadata type reference
(prefix_metadata (qualified_name (name (identifier) @type)))

(quoted_name) @string.special
(short_name) @label
(enumeration_member (name (identifier) @constant))
(control_node (name (identifier) @label))

; Comments
(comment) @comment
(block_comment_body) @comment.block
(documentation) @comment.documentation
(comment_statement) @comment
