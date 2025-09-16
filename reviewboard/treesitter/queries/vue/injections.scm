((comment) @injection.content
  (#set! injection.language "comment"))

; <style>...</style>
; <style blocking> ...</style>
; Add "lang" to predicate check so that vue/svelte can inherit this
; without having this element being captured twice
((style_element
  (start_tag) @_no_type_lang
  (raw_text) @injection.content)
  (#not-match? @_no_type_lang "\\slang\\s*=")
  (#not-match? @_no_type_lang "\\stype\\s*=")
  (#set! injection.language "css"))

((style_element
  (start_tag
    (attribute
      (attribute_name) @_type
      (quoted_attribute_value
        (attribute_value) @_css)))
  (raw_text) @injection.content)
  (#eq? @_type "type")
  (#eq? @_css "text/css")
  (#set! injection.language "css"))

; <script>...</script>
; <script defer>...</script>
((script_element
  (start_tag) @_no_type_lang
  (raw_text) @injection.content)
  (#not-match? @_no_type_lang "\\slang\\s*=")
  (#not-match? @_no_type_lang "\\stype\\s*=")
  (#set! injection.language "javascript"))

; <script type="foo/bar">
(script_element
  (start_tag
    (attribute
      (attribute_name) @_attr
      (#eq? @_attr "type")
      (quoted_attribute_value
        (attribute_value) @injection.language)))
  (raw_text) @injection.content
  (#gsub! @injection.language "(?s)(.+)/(.+)" "\\2"))

; <script type="importmap">
((script_element
  (start_tag
    (attribute
      (attribute_name) @_attr
      (#eq? @_attr "type")
      (quoted_attribute_value
        (attribute_value) @_type)))
  (raw_text) @injection.content)
  (#eq? @_type "importmap")
  (#set! injection.language "json"))

; <script type="module">
((script_element
  (start_tag
    (attribute
      (attribute_name) @_attr
      (#eq? @_attr "type")
      (quoted_attribute_value
        (attribute_value) @_type)))
  (raw_text) @injection.content)
  (#eq? @_type "module")
  (#set! injection.language "javascript"))

; <a style="/* css */">
((attribute
  (attribute_name) @_attr
  (quoted_attribute_value
    (attribute_value) @injection.content))
  (#eq? @_attr "style")
  (#set! injection.language "css"))

; lit-html style template interpolation
; <a @click=${e => console.log(e)}>
; <a @click="${e => console.log(e)}">
((attribute
  (quoted_attribute_value
    (attribute_value) @injection.content))
  (#match? @injection.content "\\$\\{")
  (#offset! @injection.content 0 2 0 -1)
  (#set! injection.language "javascript"))

((attribute
  (attribute_value) @injection.content)
  (#match? @injection.content "\\$\\{")
  (#offset! @injection.content 0 2 0 -2)
  (#set! injection.language "javascript"))

; <input pattern="[0-9]"> or <input pattern=[0-9]>
(element
  (_
    (tag_name) @_tagname
    (#eq? @_tagname "input")
    (attribute
      (attribute_name) @_attr
      [
        (quoted_attribute_value
          (attribute_value) @injection.content)
        (attribute_value) @injection.content
      ]
      (#eq? @_attr "pattern"))
    (#set! injection.language "regex")))

; <input type="checkbox" onchange="this.closest('form').elements.output.value = this.checked">
(attribute
  (attribute_name) @_name
  (#match? @_name "^on[a-z]+$")
  (quoted_attribute_value
    (attribute_value) @injection.content)
  (#set! injection.language "javascript"))

; <script lang="css">
((style_element
  (start_tag
    (attribute
      (attribute_name) @_lang
      (quoted_attribute_value
        (attribute_value) @injection.language)))
  (raw_text) @injection.content)
  (#eq? @_lang "lang")
  (#any-of? @injection.language "css" "scss"))

; TODO: When nvim-treesitter has postcss and less parsers, use @injection.language and @injection.content instead
; <script lang="scss">
(style_element
  (start_tag
    (attribute
      (attribute_name) @_lang
      (quoted_attribute_value
        (attribute_value) @_scss)))
  (raw_text) @injection.content
  (#eq? @_lang "lang")
  (#any-of? @_scss "less" "postcss" "sass")
  (#set! injection.language "scss"))

; <script lang="js">
((script_element
  (start_tag
    (attribute
      (attribute_name) @_lang
      (quoted_attribute_value
        (attribute_value) @_js)))
  (raw_text) @injection.content)
  (#eq? @_lang "lang")
  (#eq? @_js "js")
  (#set! injection.language "javascript"))

; <script lang="ts">
((script_element
  (start_tag
    (attribute
      (attribute_name) @_lang
      (quoted_attribute_value
        (attribute_value) @_ts)))
  (raw_text) @injection.content)
  (#eq? @_lang "lang")
  (#eq? @_ts "ts")
  (#set! injection.language "typescript"))

; <script lang="tsx">
; <script lang="jsx">
(script_element
  (start_tag
    (attribute
      (attribute_name) @_attr
      (quoted_attribute_value
        (attribute_value) @injection.language)))
  (#eq? @_attr "lang")
  (#any-of? @injection.language "tsx" "jsx")
  (raw_text) @injection.content)

((interpolation
  (raw_text) @injection.content)
  (#set! injection.language "typescript"))

(directive_attribute
  (quoted_attribute_value
    (attribute_value) @injection.content
    (#set! injection.language "typescript")))

(template_element
  (start_tag
    (attribute
      (quoted_attribute_value
        (attribute_value) @injection.language)))
  (text) @injection.content
  (#eq? @injection.language "pug"))
