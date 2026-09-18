(value_definition
  (let_binding
    ; let f x = 1 but not let x = 1
    (parameter)+
    body: (_) @function.inner)) @function.outer

(value_definition
  (let_binding
    ; let f = function | A | B -> body
    body: (function_expression) @function.inner)) @function.outer

(value_definition
  (let_binding
    ; let f = fun x -> body
    body: (fun_expression) @function.inner)) @function.outer

; standalone function expression, e.g. List.iter ~f:(function | A | B -> body)
(parenthesized_expression
  (function_expression) @function.inner) @function.outer

; standalone function expression, e.g. List.iter ~f:(fun x -> body)
(parenthesized_expression
  (fun_expression) @function.inner) @function.outer

(method_definition
  body: (_) @function.inner) @function.outer

; module M = struct ... end
(module_definition
  (module_binding
    body: (structure) @class.inner)) @class.outer

(class_definition
  (class_binding
    body: (_) @class.inner)) @class.outer
