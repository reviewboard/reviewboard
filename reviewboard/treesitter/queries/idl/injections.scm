((comment) @injection.content
  (#match? @injection.content "/[*/][!*/]<?[^a-zA-Z]")
  (#set! injection.language "doxygen"))

((comment) @injection.content
  (#not-match? @injection.content "/[*/][!*/]<?[^a-zA-Z]")
  (#not-match? @injection.content "//@[a-zA-Z]")
  (#set! injection.language "comment"))
