; highlights.scm

[
 (annotation)
 (inline_comment)
 (rest_of_line_comment)
 (old_style_twic_section_comment)
] @comment

(tagpair_delimiter_open) @punctuation.bracket
(tagpair_delimiter_close) @punctuation.bracket
(tagpair_key) @type
(tagpair tagpair_value_delimiter: (double_quote) @string)
(tagpair_value_contents) @string

(movetext (move_number) @function)
(movetext (san_move) @function)
(movetext (lan_move) @function)

(variation_delimiter_open) @operator
(variation_delimiter_close) @operator
(variation_movetext variation_san_move: (san_move) @operator)
(variation_movetext variation_move_number: (move_number) @operator)

(result_code) @variable

(ERROR) @property
