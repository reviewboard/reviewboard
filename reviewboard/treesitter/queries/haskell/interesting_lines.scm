(decl/function) @function.outer

; also treat function signature as @function.outer
(signature) @function.outer

; treat signature with function as @function.outer
(((decl/signature
  name: (_) @_sig_name) @function.outer
  .
  (decl/function
    name: (_) @_func_name) @function.outer)
  (#eq? @_sig_name @_func_name))

(class) @class.outer

(instance
  "where"?
  .
  _ @class.inner) @class.outer
