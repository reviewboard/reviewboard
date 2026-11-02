;; *******************************************************************
;; Comments
;; *******************************************************************

[(block_comment) (line_comment)] @comment

;; *******************************************************************
;; Keywords
;; *******************************************************************

[
 ;; Reserved Words Core
 "abstype" "and" "andalso" "as" "case" "datatype" "do" "else" "end"
 "exception" "fn" "fun" "handle" "if" "in" "infix" "infixr" "let"
 "local" "nonfix" "of" "op" "open" "orelse" "raise" "rec" "then"
 "type" "val" "with" "withtype" "while"
 ;; Reserved Words Modules
 "eqtype" "functor" "include" "sharing" "sig" "signature" "struct"
 "structure" "where"
] @keyword

;; Because tree-sitter uses context-sensitive scanning, a reserved word can be
;; parsed as an identifier if that reserved word cannot occur in a particular
;; context; for example, `val x = struct` is parsed as a valbind with `struct`
;; parsed as a vid.  Highlight such misinterpreted identifiers.
([(vid) (tycon) (strid) (sigid) (fctid)] @id
 (#any-of? @id
           ;; Reserved Words Core
           "abstype" "and" "andalso" "as" "case" "datatype" "do" "else" "end"
           "exception" "fn" "fun" "handle" "if" "in" "infix" "infixr" "let"
           "local" "nonfix" "of" "op" "open" "orelse" "raise" "rec" "then"
           "type" "val" "with" "withtype" "while"
           ;; Reserved Words Modules
           "eqtype" "functor" "include" "sharing" "sig" "signature" "struct"
           "structure" "where")) @error

;; As an additional special case, The Defn of SML excludes `*` from tycon.
([(tycon)] @id (#eq? @id "*")) @error

;; *******************************************************************
;; Punctuation
;; *******************************************************************

["(" ")" "[" "]" "{" "}"] @punctuation.bracket
["." "," ":" ";" "|" "=>" ":>"] @punctuation.delimiter

;; *******************************************************************
;; Constants
;; *******************************************************************

[(integer_scon) (word_scon) (real_scon)] @number
[(string_scon) (char_scon)] @string

;; *******************************************************************
;; Types
;; *******************************************************************

(fn_ty "->" @type)
(tuple_ty "*" @type)
(paren_ty ["(" ")"] @type)
(tyvar_ty (tyvar) @type)
(record_ty
 ["{" "," "}"] @type
 (tyrow [(lab) ":"] @type)?
 (ellipsis_tyrow ["..." ":"] @type)?)
(tycon_ty
 (tyseq ["(" "," ")"] @type)?
 (longtycon) @type)

;; *******************************************************************
;; Constructors
;; *******************************************************************

;; Assume value identifiers starting with capital letter are constructors
((vid) @vid (#match? @vid "^[A-Z].*")) @constructor
; (longvid ((vid) @vid (#match? @vid "^[A-Z].*"))) @constructor

;; "true", "false", "nil", "::", and "ref" are built-in constructors
((vid) @vid (#any-of? @vid "true" "false" "nil" "::" "ref")) @constant.builtin
; (longvid ((vid) @vid (#any-of? @vid "true" "false" "nil" "::" "ref"))) @constant.builtin

;; *******************************************************************
;; Modules
;; *******************************************************************

[(strid) (sigid) (fctid)] @module
