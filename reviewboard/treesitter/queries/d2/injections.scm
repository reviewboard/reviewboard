(label_codeblock
  (codeblock_language) @injection.language
  (codeblock_content) @injection.content)

((label_codeblock
  (codeblock_content) @injection.content)
  (#set! injection.language "markdown"))

((label_codeblock
  (codeblock_language) @injection.language
  (codeblock_content) @injection.content)
  (#any-of? @injection.language
    "md" "")
  (#set! injection.language "markdown"))
