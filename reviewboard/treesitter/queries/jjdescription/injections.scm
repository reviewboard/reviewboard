((comment_content) @injection.content
  (#set! injection.language "comment"))

((rest) @injection.content
  (#match? @injection.content "^diff")
  (#set! injection.language "diff"))
