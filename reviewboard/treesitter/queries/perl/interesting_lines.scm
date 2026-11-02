; class
(package_statement
  (block) @class.inner) @class.outer

(class_statement
  (block) @class.inner) @class.outer

(role_statement
  (block) @class.inner) @class.outer

; function
(subroutine_declaration_statement
  body: (block) @function.inner) @function.outer

(method_declaration_statement
  body: (block) @function.inner) @function.outer

(anonymous_subroutine_expression
  body: (block) @function.inner) @function.outer
