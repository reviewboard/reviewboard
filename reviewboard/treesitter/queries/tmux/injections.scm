((shell) @injection.content
  (#set! injection.language "bash"))

(comment
  (body) @injection.content
  (#set! injection.language "comment"))

(set_option_directive
  (command)
  (option) @_option
  (value
    content: (string) @injection.content)
  (#any-of? @_option
    "set-titles-string" "window-status-format" "window-status-current-format" "status-left"
    "status-right")
  (#set! injection.language "tmuxf"))

(inputs
  content: (string) @injection.content
  (#set! injection.language "tmuxf"))

(if_statement
  (if_keyword)
  (condition
    (string) @injection.content)
  (#set! injection.language "tmuxf"))

(if_statement
  (elif_keyword)
  (condition
    (string) @injection.content)
  (#set! injection.language "tmuxf"))
