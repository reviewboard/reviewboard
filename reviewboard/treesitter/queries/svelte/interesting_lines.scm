(element) @function.outer

(script_element) @function.outer

(style_element) @function.outer

((element
  (start_tag
    (tag_name) @_tag)) @class.outer
  (#match? @_tag "^(html|section|h[0-9]|header|title|head|body)$"))
