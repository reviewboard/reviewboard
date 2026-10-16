((comment) @injection.content
  (#set! injection.language "comment"))


([
  (html_comment)
  (razor_comment)
] @injection.content
  (#set! injection.language "comment"))

((element) @injection.content
  (#set! injection.language "html")
  (#set! injection.combined))
