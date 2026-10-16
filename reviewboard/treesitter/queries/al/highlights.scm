; AL Language (v2) - Tree-sitter Syntax Highlighting Queries
; See: https://tree-sitter.github.io/tree-sitter/syntax-highlighting
;
; Keywords are exposed as named nodes (e.g., if_keyword, table_keyword) for
; precise highlighting. begin/end are named at depth 0 via external scanner.
; =============================================================================
; Comments
; =============================================================================
(comment) @comment.line

(multiline_comment) @comment.block

; =============================================================================
; Preprocessor Directives
; =============================================================================
[
  (preproc_if)
  (preproc_else)
  (preproc_elif)
  (preproc_endif)
  (pragma)
  (preproc_region)
  (preproc_endregion)
  (preproc_define)
  (preproc_undef)
] @keyword.directive

; =============================================================================
; Keywords - Control Flow
; =============================================================================
[
  (if_keyword)
  (then_keyword)
  (else_keyword)
  (case_keyword)
  (of_keyword)
  (while_keyword)
  (do_keyword)
  (for_keyword)
  (foreach_keyword)
  (in_keyword)
  (repeat_keyword)
  (until_keyword)
  (exit_keyword)
  (break_keyword)
  (continue_keyword)
  (with_keyword)
  (asserterror_keyword)
  (to_keyword)
  (downto_keyword)
  (begin_keyword)
  (end_keyword)
] @keyword.control

; =============================================================================
; Keywords - Declarations
; =============================================================================
[
  (procedure_keyword)
  (trigger_keyword)
  (var_keyword)
  (event_keyword)
] @keyword.declaration

; =============================================================================
; Keywords - Object Types
; =============================================================================
[
  (table_keyword)
  (tableextension_keyword)
  (page_keyword)
  (pageextension_keyword)
  (codeunit_keyword)
  (report_keyword)
  (reportextension_keyword)
  (query_keyword)
  (xmlport_keyword)
  (enum_keyword)
  (enumextension_keyword)
  (interface_keyword)
  (controladdin_keyword)
  (dotnet_keyword)
  (profile_keyword)
  (profileextension_keyword)
  (permissionset_keyword)
  (permissionsetextension_keyword)
  (entitlement_keyword)
  (pagecustomization_keyword)
  ; TestPage / TestRequestPage sit in the same object_reference_type choice as
  ; the object types above (`TestPage "Customer Card"`), so they belong here and
  ; not with the section kinds.
  (testpage_keyword)
  (testrequestpage_keyword)
] @keyword.type

; =============================================================================
; Keywords - Structure
; =============================================================================
[
  (namespace_keyword)
  (using_keyword)
  (extends_keyword)
  (implements_keyword)
  (customizes_keyword)
] @keyword.import

; =============================================================================
; Keywords - Sections
; =============================================================================
[
  (fields_keyword)
  (keys_keyword)
  (key_keyword)
  (fieldgroups_keyword)
  (fieldgroup_keyword)
  (actions_keyword)
  (layout_keyword)
  (area_keyword)
  (group_keyword)
  (repeater_keyword)
  (cuegroup_keyword)
  (fixed_keyword)
  (grid_keyword)
  (part_keyword)
  (systempart_keyword)
  (chartpart_keyword)
  (usercontrol_keyword)
  (dataset_keyword)
  (elements_keyword)
  (dataitem_keyword)
  (column_keyword)
  (filter_keyword)
  ; The where()/field()/const()/upperlimit() markers, named in 4.0.0. Before
  ; that, filter() was the only one of the four that could be captured at all.
  (where_keyword)
  (field_keyword)
  (const_keyword)
  (upperlimit_keyword)
  (labels_keyword)
  (rendering_keyword)
  (requestpage_keyword)
  (schema_keyword)
  (views_keyword)
  (view_keyword)
  ; Named in the losslessness pass. Every one of these was a bare kw() at its
  ; call site, i.e. a token(PATTERN) that tree-sitter hides, so the bytes were
  ; lexed and landed in no node: unhighlightable and unmatchable, no matter how
  ; the pattern was written. `field` above and `field(1; "No."; Code[20])` here
  ; are the same word, and only the first one could be captured.
  (value_keyword)
  (label_keyword)
  (separator_keyword)
  (assembly_keyword)
  (type_keyword)
  (tabledata_keyword)
  (system_keyword)
  ; No (access_keyword): the rule went with interface_declaration's dead header
  ; `Access = X` clause. AL writes interface access as a body PROPERTY, where
  ; `Access` is a property_name. Naming a type the grammar does not declare is
  ; not a dead pattern -- tree_sitter.Query raises QueryError and takes `qc run`
  ; down on a traceback instead of reporting a finding.
  (sorting_keyword)
  (order_keyword)
  (ascending_keyword)
  (descending_keyword)
  (lookup_keyword)
  (comment_keyword)
  (locked_keyword)
  (maxlength_keyword)
  ; Action-family declarations
  (action_keyword)
  (actionref_keyword)
  (systemaction_keyword)
  (customaction_keyword)
  (fileuploadaction_keyword)
  ; Extension modifications
  (add_keyword)
  (addfirst_keyword)
  (addlast_keyword)
  (addafter_keyword)
  (addbefore_keyword)
  (modify_keyword)
  (movefirst_keyword)
  (movelast_keyword)
  (moveafter_keyword)
  (movebefore_keyword)
  ; Section, area and element kinds. These gained rules in 4.0.0 — which is what
  ; made `area(Content)` and `textelement(Foo)` produce a node at all — but were
  ; never added here, so the nodes existed and no shipped query reached them.
  ; They are the whole remaining uncaptured-keyword population.
  (content_keyword)
  (factboxes_keyword)
  (processing_keyword)
  (rolecenter_keyword)
  (navigation_keyword)
  (creation_keyword)
  (reporting_keyword)
  (promoted_keyword)
  (sections_keyword)
  (embedding_keyword)
  (systemactions_keyword)
  (prompting_keyword)
  (prompt_keyword)
  (promptoptions_keyword)
  (promptguide_keyword)
  (analysisviews_keyword)
  (analysisview_keyword)
  ; XMLPort element and attribute kinds
  (tableelement_keyword)
  (textelement_keyword)
  (fieldelement_keyword)
  (textattribute_keyword)
  (fieldattribute_keyword)
] @keyword.structure

; =============================================================================
; Keywords - Modifiers
; =============================================================================
[
  (local_keyword)
  (internal_keyword)
  (protected_keyword)
  (temporary_keyword)
  (public_keyword)
] @keyword.modifier

; Procedure modifier (access modifiers on procedures)
(procedure_modifier) @keyword.modifier

; Object type keyword (used in permission sets, database refs, etc.)
(object_type_keyword) @keyword

; =============================================================================
; Operators
; =============================================================================
; Assignment operator.
; Both patterns are needed and they match disjoint sites. `:=` in an assignment
; is an `assignment_operator` node — a distinct token from the literal ':=' in
; for_statement — so the bare string below only ever matched the for-statement
; one, and no assignment was highlighted at all until assignment_operator was
; named in 4.0.0. The named pattern also covers `+=`, `-=`, `*=` and `/=`, which
; no pattern here matched before.
(assignment_operator) @operator

":=" @operator

; AL filter operators inside a filter() / TableRelation filter value: <> | = > <
; >= <= & @ * %, in any run. Same story as assignment_operator one release
; earlier — an inline token(PATTERN) with no node, so `Type = const(Item) & "No."
; <> ''` had two uncoloured operators and no pattern could reach them. 890
; occurrences in BC.History, 354 of them the bare `|` alternation.
(filter_operator) @operator

; Arithmetic operators
[
  "+"
  "-"
  "*"
  "/"
] @operator

; Comparison and binding operators, as bare tokens.
;
; Bare rather than via the parent node, because that is what this file already
; does for "+" "-" "*" "/" above — those are children of additive_expression and
; multiplicative_expression and are captured directly. `(comparison_operator)
; @operator` below is the odd one out: it captures the WRAPPER, and a wrapper
; capture does not capture the anonymous token inside it. The two spans are
; identical, so `a <> b` was already coloured — but a consumer writing
; `"<>" @operator`, the obvious pattern, matched nothing.
;
; `=` is the one with real coverage to gain, and it is an operator in every AL
; position, never structural punctuation the way ";" and "," are: it binds a
; property to its value (`Caption = 'X'`), a filter field to its expression
; (`where("No." = field("No."))`), a permission to its level (`tabledata X = R`),
; a label to its text, and an interface to its implementation. Measured over
; 3,000 corpus files, 107,958 of these sat in `property` alone and none of them
; were reachable — only link_value's `=` had a pattern.
;
; No "&&"/"||": they were never preprocessor forms of and/or. alc rejects both in
; an #if condition (AL0631), and B2 removed them from the grammar.
[
  "="
  "<>"
  ">"
  "<"
  ">="
  "<="
] @operator

; Comparison operators (named node wrapping =, <>, <, >, <=, >=)
(comparison_operator) @operator

; Range operator
".." @operator

; Member access
"." @punctuation.delimiter

; Enum/scope qualifier
"::" @operator

; Ternary conditional
"?" @operator

; Keyword operators. These are case-insensitive tokens aliased to a single
; lowercase node name, so one entry matches every source casing. `in` is
; covered by (in_keyword) in the keyword block above.
[
  "and"
  "or"
  "xor"
  "not"
  "div"
  "mod"
] @keyword.operator

; `is` and `as` are named nodes rather than bare strings because they were the
; declared `operator` field of is_expression/as_expression, and a hidden token
; in a field() takes the field down with it — the field returned None and the
; keyword was in no node. The preproc `or`/`and` are NOT listed separately: they
; are aliased to the same anonymous "or"/"and" the block above already matches.
[
  (is_keyword)
  (as_keyword)
] @keyword.operator

; =============================================================================
; Punctuation
; =============================================================================
";" @punctuation.delimiter

":" @punctuation.delimiter

"," @punctuation.delimiter

"(" @punctuation.bracket

")" @punctuation.bracket

"[" @punctuation.bracket

"]" @punctuation.bracket

"{" @punctuation.bracket

"}" @punctuation.bracket

; =============================================================================
; Literals
; =============================================================================
(string_literal) @string

(integer) @number

(decimal) @number.float

(biginteger_literal) @number

(boolean) @constant.builtin

(date_literal) @string.special

(time_literal) @string.special

(datetime_literal) @string.special

; XmlPort Namespaces = prefix = 'uri', ... (namespace_pair, keyed by name since B4).
; After the generic string capture so the URI's more specific capture wins.
(namespace_pair prefix: (_) @namespace)
(namespace_pair uri: (string_literal) @string.special.url)

; =============================================================================
; Types
; =============================================================================
; Built-in types (Integer, Text, Boolean, Date, etc.)
(basic_type) @type.builtin

; Parameterized built-in types
(text_type) @type.builtin

(code_type) @type.builtin

; The type keywords themselves. The container patterns above and below span the
; keyword's bytes, so this is not about colour — it is about reach. Until the
; losslessness pass these keywords were in no node at all, so a consumer could
; not capture `Record` on its own, ask where the type name starts, or tell
; `List of [Integer]` from its element type by node. `record_keyword` alone
; occurs 305,922 times in BC.History.
[
  (record_keyword)
  (code_keyword)
  (text_keyword)
  (option_keyword)
  (array_keyword)
  (list_keyword)
  (dictionary_keyword)
] @type.builtin

; Record type references
(record_type
  reference: [
    (identifier)
    (quoted_identifier)
  ] @type)

; Object reference types (Codeunit, Page, Report, etc.)
(object_reference_type
  reference: [
    (identifier)
    (quoted_identifier)
    (integer)
  ] @type)

; Array, List, Dictionary types
(array_type) @type

(list_type) @type

(dictionary_type) @type

; Option type
(option_type) @type

; Type specifications
(type_specification) @type

; DotNet type references
(dotnet_type
  reference: [
    (identifier)
    (quoted_identifier)
  ] @type)

; =============================================================================
; Object Declarations
; =============================================================================
; Tables
(table_declaration
  object_id: (integer) @constant)

(table_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Pages
(page_declaration
  object_id: (integer) @constant)

(page_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Codeunits
(codeunit_declaration
  object_id: (integer) @constant)

(codeunit_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Reports
(report_declaration
  object_id: (integer) @constant)

(report_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Queries
(query_declaration
  object_id: (integer) @constant)

(query_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; XMLports
(xmlport_declaration
  object_id: (integer) @constant)

(xmlport_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Enums
(enum_declaration
  object_id: (integer) @constant)

(enum_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Interfaces
(interface_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; ControlAddins
(controladdin_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Profiles
(profile_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Permission Sets
(permissionset_declaration
  object_id: (integer) @constant)

(permissionset_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Entitlements
(entitlement_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Page Customizations
(pagecustomization_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; DotNet
(dotnet_declaration) @type

; =============================================================================
; Extension Declarations
; =============================================================================
(tableextension_declaration
  object_id: (integer) @constant)

(tableextension_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

(pageextension_declaration
  object_id: (integer) @constant)

(pageextension_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

(enumextension_declaration
  object_id: (integer) @constant)

(enumextension_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

(reportextension_declaration
  object_id: (integer) @constant)

(reportextension_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

(profileextension_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

(permissionsetextension_declaration
  object_id: (integer) @constant)

(permissionsetextension_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; Split declarations (preprocessor-split object headers)
(preproc_split_declaration
  object_id: (integer) @constant)

(preproc_split_declaration
  object_name: [
    (identifier)
    (quoted_identifier)
  ] @type.definition)

; =============================================================================
; Procedures and Triggers
; =============================================================================
; Procedure names
(procedure
  name: [
    (identifier)
    (quoted_identifier)
  ] @function.definition)

; Event declarations
(event_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @function.definition)

; Trigger names
(trigger_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @function.definition)

; Scoped member-trigger name (`Object::Member`)
(trigger_declaration
  name: (member_trigger_name
    object: [
      (identifier)
      (quoted_identifier)
    ] @type
    member: [
      (identifier)
      (quoted_identifier)
    ] @function.definition))

; Interface procedures
(interface_procedure
  name: [
    (identifier)
    (quoted_identifier)
  ] @function.definition)

; Split procedures (preprocessor-split)
(preproc_split_procedure
  name: [
    (identifier)
    (quoted_identifier)
  ] @function.definition)

; =============================================================================
; Fields and Variables
; =============================================================================
; Table field declarations
(field_declaration
  id: (integer) @constant)

(field_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @property.definition)

; Variable declarations
(variable_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @variable.definition)

; Parameters
(parameter
  name: [
    (identifier)
    (quoted_identifier)
  ] @variable.parameter)

; Label declarations
(label_declaration
  name: (identifier) @constant.definition)

; Enum value declarations
(enum_value_declaration
  value_id: (integer) @constant)

(enum_value_declaration
  value_name: [
    (identifier)
    (quoted_identifier)
  ] @constant.definition)

; Key declarations
(key_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @property.definition)

; Fieldgroup declarations
(fieldgroup_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @property.definition)

; Return values
(procedure
  return_value: [
    (identifier)
    (quoted_identifier)
  ] @variable.definition)

(trigger_declaration
  return_value: [
    (identifier)
    (quoted_identifier)
  ] @variable.definition)

; For loop variables
(for_statement
  variable: (identifier) @variable)

; Foreach loop variables
(foreach_statement
  variable: (identifier) @variable)

; =============================================================================
; Expressions
; =============================================================================
; Direct function calls
(call_expression
  function: (identifier) @function.call)

; Method calls on objects
(call_expression
  function: (member_expression
    member: (identifier) @function.method.call))

; Member expression components
(member_expression
  object: (identifier) @variable)

(member_expression
  member: (identifier) @property)

; Database references
(database_reference
  table_name: [
    (identifier)
    (quoted_identifier)
  ] @type)

; Qualified enum values
(qualified_enum_value
  enum_type: [
    (identifier)
    (quoted_identifier)
  ] @type)

(qualified_enum_value
  value: [
    (identifier)
    (quoted_identifier)
  ] @constant)

; Option members
(option_member) @constant

; =============================================================================
; Actions
; =============================================================================
(action_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @function)

(actionref_declaration
  action_name: [
    (identifier)
    (quoted_identifier)
  ] @function)

(customaction_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @function)

(systemaction_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @function)

(fileuploadaction_declaration
  name: [
    (identifier)
    (quoted_identifier)
  ] @function)

(separator_action
  name: [
    (identifier)
    (quoted_identifier)
  ] @punctuation.special)

; =============================================================================
; Namespace and Using
; =============================================================================
(namespace_declaration
  name: (namespace_name) @module)

(using_statement
  namespace: (namespace_name) @module)

; =============================================================================
; Implements Clause
; =============================================================================
(implements_clause
  interface: [
    (identifier)
    (quoted_identifier)
  ] @type)

; Implementation mappings -- Implementation, DefaultImplementation,
; UnknownValueImplementation. Single-entry and comma-separated forms both parse
; to implementation_value (issue #20), so these two rules cover every site.
; Until then a one-entry mapping was a comparison_expression and its two names
; took the generic identifier highlight.
(implementation_value
  interface: [
    (identifier)
    (quoted_identifier)
  ] @type)

(implementation_value
  implementation: [
    (identifier)
    (quoted_identifier)
  ] @type)

; =============================================================================
; Attributes
; =============================================================================
(attribute_item) @attribute

(attribute_content
  name: (identifier) @attribute)

; =============================================================================
; Properties
; =============================================================================
; Property name
(property
  name: (property_name) @property)

; Keyword identifiers (contextual keywords used as values)
(keyword_identifier) @keyword

; Link values — DataItemLink, RunPageLink, SubPageLink, ColumnFilter,
; DataItemTableFilter, LinkFields. Single-entry and comma-separated links both
; parse to link_value, so these rules cover every link site.
;
; The enclosing field()/const()/upperlimit()/filter() keyword is a named node
; and is highlighted with the other structure keywords above. Until 4.0.0 only
; filter() was: the other three were bare kw(), i.e. hidden pattern tokens that
; no query could reach, which is also why `where(X = field(N))` and
; `where(X = const(N))` produced identical trees.
; Target field, left of the '='
(link_value
  field: [
    (identifier)
    (quoted_identifier)
  ] @property)

; (The '=' joining a link_value's target and source is covered by the general
; "=" pattern in the operator block above, which subsumes the link_value-only
; pattern that used to live here.)
; Dotted source `DataItem."Field"` — the dataitem name. The field itself is
; covered by the source-field rule below, which anchors to the last child.
(link_value
  value: (identifier) @variable
  "."
  value: (_))

; Source field: the bare form, the dotted form's field, and the argument of
; field()/const()/filter()/upperlimit(). Anchored to the last named child so it
; never re-captures the dataitem name above. Literal arguments such as
; `const(0)` or `const('x')` are deliberately excluded and keep their own
; literal highlighting.
(link_value
  value: [
    (identifier)
    (quoted_identifier)
  ] @property .)

; =============================================================================
; Query and Report Elements
; =============================================================================
; Query dataitems
(query_dataitem
  name: [
    (identifier)
    (quoted_identifier)
  ] @variable)

(query_dataitem
  table_name: [
    (identifier)
    (quoted_identifier)
  ] @type)

; Query columns
(query_column
  name: [
    (identifier)
    (quoted_identifier)
  ] @property)

; Report dataitems
(report_dataitem
  name: [
    (identifier)
    (quoted_identifier)
  ] @variable)

(report_dataitem
  table_name: [
    (identifier)
    (quoted_identifier)
  ] @type)

; Report columns
(report_column
  name: [
    (identifier)
    (quoted_identifier)
  ] @property)

; =============================================================================
; Page Fields
; =============================================================================
(page_field
  name: [
    (identifier)
    (quoted_identifier)
  ] @property)

; =============================================================================
; XMLport Elements
; =============================================================================
(xmlport_element
  name: [
    (identifier)
    (quoted_identifier)
  ] @property)

(xmlport_attribute
  name: [
    (identifier)
    (quoted_identifier)
  ] @property)

; =============================================================================
; View Definitions
; =============================================================================
(view_definition
  name: [
    (identifier)
    (quoted_identifier)
  ] @property.definition)

; =============================================================================
; DotNet
; =============================================================================
(assembly_declaration
  name: [
    (string_literal)
    (quoted_identifier)
    (dotnet_assembly_name)
  ] @string)

(type_declaration) @type

; =============================================================================
; Permission Types
; =============================================================================
(permission_type) @keyword

(tabledata_permission
  table_name: [
    (identifier)
    (quoted_identifier)
  ] @type)

; =============================================================================
; Errors
; =============================================================================
(ERROR) @error
