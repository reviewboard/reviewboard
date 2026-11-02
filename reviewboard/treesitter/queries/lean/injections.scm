; Language injections for tree-sitter-lean.

; Doc comments are Markdown / Verso content.
((doc_comment) @injection.content
  (#set! injection.language "markdown"))

((module_doc_comment) @injection.content
  (#set! injection.language "markdown"))

; Raw string contents stay plain; no injection beyond default text.
