(class_declaration
  body: (class_body
    .
    "{"
    _+ @class.inner
    "}")) @class.outer

(class_declaration
  body: (enum_class_body
    .
    "{"
    _+ @class.inner
    "}")) @class.outer

(function_declaration
  body: (function_body
    .
    "{"
    _+ @function.inner
    "}")) @function.outer

(lambda_literal
  ("{"
    _+ @function.inner
    "}")) @function.outer
