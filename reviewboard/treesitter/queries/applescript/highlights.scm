; Keywords
[
  "tell"
  "end"
  "if"
  "then"
  "else"
  "repeat"
  "times"
  "while"
  "until"
  "from"
  "to"
  "by"
  "in"
  "try"
  "on"
  "error"
  "set"
  "copy"
  "return"
  "exit"
  "considering"
  "ignoring"
  "with"
  "without"
  "timeout"
  "transaction"
  "of"
  "seconds"
  "use"
  "scripting"
  "additions"
  "application"
  "version"
  "script"
  "property"
  "given"
  "my"
  "its"
  "exists"
  "and"
  "or"
  "not"
  "as"]
@keyword

; Control flow keywords
[
  "if"
  "then"
  "else"
  "repeat"
  "exit"
  "return"
  "try"
  "error"]
@keyword.control

; Boolean literals
(boolean)
@constant.builtin.boolean

; Special constants
(missing_value)
@constant.builtin

(text_constant)
@constant.builtin

; Current application (special constant)
(current_application)
@constant.builtin

; Numbers
(integer)
@constant.numeric.integer
(real)
@constant.numeric.float

; Strings
(string)
@string

; Comments
(comment)
@comment

; Identifiers
(identifier)
@variable

; Function/Handler definitions
(simple_handler
  name:
  (identifier)
  @function)

(positional_handler
  name:
  (identifier)
  @function)

(labeled_handler
  name:
  (identifier)
  @function)

; Script object definitions (like classes)
(script_statement
  name:
  (identifier)
  @type)

; Handler end names
(simple_handler
  end_name:
  (identifier)
  @function)

(positional_handler
  end_name:
  (identifier)
  @function)

(labeled_handler
  end_name:
  (identifier)
  @function)

; Handler parameters
(parameter_list
  (identifier)
  @variable.parameter)

(direct_parameter
  parameter:
  (identifier)
  @variable.parameter)

(labeled_parameter
  parameter:
  (identifier)
  @variable.parameter)

(boolean_parameter
  parameter:
  (identifier)
  @variable.parameter)

; Property names in property statements
(property_statement
  name:
  (identifier)
  @property)

; Record keys
(record_entry
  key:
  (_)
  @property)

; Application names
(application_expression
  name:
  (string)
  @string.special)

(application_expression
  name:
  (identifier)
  @variable)

; Script references
(script_reference
  (string)
  @string.special)

; Type casts
(type_cast
  type:
  (identifier)
  @type)

; Method calls (Objective-C bridge)
(method_call
  method:
  (method_call_label)
  @function.method)

; Scripting-additions commands. Application-specific ones are not listed:
; their vocabulary comes from the target app's dictionary, so they arrive as
; ordinary multi-word command names.
[
  (system_attribute)
  (do_shell_script)
  (do_javascript)
  (path_to_command)]
@function.builtin

; Operators
[
  "="
  "≠"
  ">"
  "<"
  "≥"
  "≤"
  ">="
  "<="
  "+"
  "-"
  "*"
  "/"
  "÷"
  "^"
  "&"
  "div"
  "mod"]
@operator

; Comparison operators (word-based)
[
  "equals"
  "is equal to"
  "is equal"
  "equal to"
  "is not"
  "is not equal to"
  "is not equal"
  "isn't"
  "isn't equal to"
  "is greater than"
  "greater than"
  "comes after"
  "is less than"
  "less than"
  "comes before"
  "is greater than or equal to"
  "is greater than or equal"
  "is less than or equal to"
  "is less than or equal"
  "is"
  "contains"
  "contain"
  "does not contain"
  "doesn't contain"
  "is in"
  "is contained by"
  "is not in"
  "is not contained by"
  "starts with"
  "start with"
  "begins with"
  "begin with"
  "ends with"
  "end with"
  "whose"
  "where"
  "thru"
  "through"]
@operator

; Delimiters
[
  "("
  ")"
  "{"
  "}"
  ","]
@punctuation.delimiter

; Colon in records and labeled parameters
":"
@punctuation.delimiter

; Property access
"'s"
@punctuation.special

; Application command highlighting
(application_command
  command:
  (identifier)
  @function.call)

; Handler calls
(handler_call
  name:
  (identifier)
  @function.call)

; Tell statement targets
(tell_statement
  target:
  (identifier)
  @variable.builtin)
