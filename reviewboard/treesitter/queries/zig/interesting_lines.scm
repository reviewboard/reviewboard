; "Classes"
(VarDecl
  (_
    (_
      (ContainerDecl) @class.inner))) @class.outer

; functions
(_
  (FnProto)
  ((Block
    .
    "{"
    .
    (_) @_start @_end
    (_)? @_end
    .
    "}")
    (#make-range! "function.inner" @_start @_end))) @function.outer
