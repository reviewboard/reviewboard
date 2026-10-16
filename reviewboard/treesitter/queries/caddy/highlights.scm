[
  (http_error_code)
  (http_status_code)
  (size_number)
] @number

(snippet_name) @function

(_ directive_type: _ @keyword)


; (_ respond_or_error_option_message: _ @function.method)

(_ matcher_type: _ @function.macro)

; (_ basicauth_user_name: _ @string)
; (_ basicauth_user_pass: _ @string)
; (_ basicauth_user_pass_saltb64: _ @string)
; (_ respond_or_error_message: _ @string)

(_ path_regexp_matcher_value: _ @string)

(_ global_option_type: _ @function.method)

(_ directive_option_name: _ @function.method)

(_ directive_option_fixed_value: _ @variable.parameter)

(_ directive_option_user_string_value: _ @string)

[
  (matcher_name)
  (matcher_token)
] @tag

(header_name) @variable.parameter

[
  (header_value)
  (unix_path)
  (email_address)
  (http_message)
] @string

(comment_line) @comment

(site_address) @constant

[
  "stdout"
  "stderr"
  "discard"
  "file"

  "console"
  "json"

  "info"
  "INFO"
  "error"
  "ERROR"
] @constant.builtin

["{" "}"] @punctuation.bracket
