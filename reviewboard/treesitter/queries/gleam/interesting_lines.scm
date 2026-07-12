; class
(type_definition
  (data_constructors) @class.inner) @class.outer

; functions
(function
  body: (block
    "{"
    .
    _+ @function.inner
    .
    "}")) @function.outer

(anonymous_function
  body: (block
    "{"
    .
    _+ @function.inner
    .
    "}")) @function.outer
