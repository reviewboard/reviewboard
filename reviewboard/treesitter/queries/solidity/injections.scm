((comment) @injection.content
  (#set! injection.language "comment"))

((comment) @injection.content
  (#match? @injection.content "^///[^/]")
  (#set! injection.language "doxygen"))

((comment) @injection.content
  (#match? @injection.content "^///$")
  (#set! injection.language "doxygen"))

((comment) @injection.content
  (#match? @injection.content "(?s)^/[*][*][^*].*[*]/$")
  (#set! injection.language "doxygen"))
