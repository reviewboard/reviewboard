; Based on dlyubanevich/zed-bsl-extension at b0975ec.

(line_comment) @comment

(procedure_definition
  name: (identifier) @function)

(function_definition
  name: (identifier) @function)

(method_call
  name: (identifier) @function)

[
  (ADDHANDLER_KEYWORD)
  (AND_KEYWORD)
  (ASYNC_KEYWORD)
  (AWAIT_KEYWORD)
  (BREAK_KEYWORD)
  (CONTINUE_KEYWORD)
  (DO_KEYWORD)
  (EACH_KEYWORD)
  (ELSE_KEYWORD)
  (ELSIF_KEYWORD)
  (ENDDO_KEYWORD)
  (ENDFUNCTION_KEYWORD)
  (ENDIF_KEYWORD)
  (ENDPROCEDURE_KEYWORD)
  (ENDTRY_KEYWORD)
  (EXCEPT_KEYWORD)
  (EXPORT_KEYWORD)
  (FALSE_KEYWORD)
  (FOR_KEYWORD)
  (FUNCTION_KEYWORD)
  (GOTO_KEYWORD)
  (IF_KEYWORD)
  (IN_KEYWORD)
  (NOT_KEYWORD)
  (NULL_KEYWORD)
  (OR_KEYWORD)
  (PROCEDURE_KEYWORD)
  (RAISE_KEYWORD)
  (REMOVEHANDLER_KEYWORD)
  (RETURN_KEYWORD)
  (THEN_KEYWORD)
  (TO_KEYWORD)
  (TRUE_KEYWORD)
  (TRY_KEYWORD)
  (UNDEFINED_KEYWORD)
  (VAL_KEYWORD)
  (VAR_KEYWORD)
  (WHILE_KEYWORD)
] @keyword

[
  (PREPROC_IF_KEYWORD)
  (PREPROC_ELSE_KEYWORD)
  (PREPROC_ELSIF_KEYWORD)
  (PREPROC_ENDIF_KEYWORD)
  (PREPROC_REGION_KEYWORD)
  (PREPROC_ENDREGION_KEYWORD)
  (preproc)
] @keyword

(preprocessor
  (PREPROC_REGION_KEYWORD)
  name: (identifier) @module)

(annotation) @attribute

(operator) @operator
(NEW_KEYWORD) @constructor

[
  (string)
  (string_content)
] @string

(date) @constant
(number) @number

[
  "("
  ")"
  "["
  "]"
] @punctuation.bracket

[
  ";"
  "."
  ","
] @punctuation.delimiter
