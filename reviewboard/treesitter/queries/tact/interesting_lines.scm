; See: https://github.com/nvim-treesitter/nvim-treesitter-textobjects#built-in-textobjects
; function.inner & outer
; ----------------------
; global
(global_function
  body: (_)) @function.outer

; init
(init_function
  body: (_)) @function.outer

; bounced
(bounced_function
  body: (_)) @function.outer

; receive
(receive_function
  body: (_)) @function.outer

; external
(external_function
  body: (_)) @function.outer

; contract/trait function
(storage_function
  body: (_)) @function.outer

; class.inner & outer
; -------------------
(struct) @class.outer

(message) @class.outer

(contract) @class.outer

(trait) @class.outer
