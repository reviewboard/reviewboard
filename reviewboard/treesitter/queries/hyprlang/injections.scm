((comment) @injection.content
  (#set! injection.language "comment"))

(exec
  (string) @injection.content
  (#set! injection.language "bash"))

((keyword
  (name) @_bind
  (params
    .
    (_)
    .
    (_)
    .
    (_)?
    .
    (string) @_exec
    .
    (string) @injection.content))
  (#match? @_bind "^bind")
  (#match? @_exec "^\\s*exec\\s*$")
  (#set! injection.language "bash"))

((assignment
  (name) @_name
  (string) @injection.content)
  (#any-of? @_name
    "lock_cmd" "unlock_cmd" "before_sleep_cmd" "after_sleep_cmd" "on-timeout" "on-resume"
    "reload_cmd")
  (#set! injection.language "bash"))
