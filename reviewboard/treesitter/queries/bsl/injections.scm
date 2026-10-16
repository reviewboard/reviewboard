; Parse static BSL string literals that start with a query-language statement
; using the standalone SDBL grammar. Keep the BSL string node shape unchanged.

((string) @injection.content
  (#match? @injection.content "^\"[\\s|]*(ВЫБРАТЬ|выбрать|SELECT|select|УНИЧТОЖИТЬ|уничтожить|DROP|drop)(\\s|$)")
  (#set! injection.language "sdbl")
  (#set! injection.include-children)
  (#strip! @injection.content "^\"|\"$|(?m)^\\s*\\| ?"))
