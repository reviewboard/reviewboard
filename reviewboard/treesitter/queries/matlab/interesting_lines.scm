(lambda
  expression: (_) @function.inner) @function.outer

(function_definition
  (block) @function.inner) @function.outer

(class_definition) @class.outer
