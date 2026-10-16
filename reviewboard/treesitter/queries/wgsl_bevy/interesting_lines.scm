(function_declaration) @function.outer

(struct_declaration
  "{"
  _+ @class.inner
  "}") @class.outer
