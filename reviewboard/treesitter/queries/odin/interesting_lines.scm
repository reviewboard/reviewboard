; procedures
(procedure_declaration
  (_
    (block
      .
      "{"
      _+ @function.inner
      "}"))) @function.outer

; classes
(struct_declaration
  "{"
  _+ @class.inner
  "}") @class.outer

(union_declaration
  "{"
  _+ @class.inner
  "}") @class.outer

(enum_declaration
  "{"
  _+ @class.inner
  "}") @class.outer
