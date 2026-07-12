(class_declaration
  body: (declaration_list
    .
    "{"
    _* @class.inner
    "}")) @class.outer

(struct_declaration
  body: (declaration_list
    .
    "{"
    _* @class.inner
    "}")) @class.outer

(record_declaration
  body: (declaration_list
    .
    "{"
    _* @class.inner
    "}")) @class.outer

(interface_declaration
  body: (declaration_list
    .
    "{"
    _+ @class.inner
    "}")) @class.outer

(enum_declaration
  body: (enum_member_declaration_list
    .
    "{"
    _* @class.inner
    "}")) @class.outer

(method_declaration
  body: (block
    .
    "{"
    _* @function.inner
    "}")) @function.outer

(method_declaration
  body: (arrow_expression_clause
    "=>"
    _+ @function.inner)) @function.outer

; method without body(abstract method/decompiled metadata)
(method_declaration
  _+
  ";") @function.outer

(property_declaration
  accessors: (accessor_list
    (accessor_declaration
      body: (block
        .
        "{"
        _* @function.inner
        "}")) @function.outer))

(property_declaration
  accessors: (accessor_list
    (accessor_declaration
      body: (arrow_expression_clause
        "=>"
        _* @function.inner)) @function.outer))

(indexer_declaration
  accessors: (accessor_list
    (accessor_declaration
      body: (arrow_expression_clause
        "=>"
        _+ @function.inner)) @function.outer))

(indexer_declaration
  accessors: (accessor_list
    (accessor_declaration
      body: (block
        .
        "{"
        _* @function.inner
        "}")) @function.outer))

(conversion_operator_declaration
  body: (block
    .
    "{"
    _* @function.inner
    "}")) @function.outer

(conversion_operator_declaration
  body: (arrow_expression_clause
    "=>"
    _+ @function.inner)) @function.outer

(operator_declaration
  body: (block
    .
    "{"
    _* @function.inner
    "}")) @function.outer

; operator without body(abstract/decompiled metadata)
(operator_declaration
  _+
  ";") @function.outer

(operator_declaration
  body: (arrow_expression_clause
    "=>"
    _+ @function.inner)) @function.outer

(constructor_declaration
  body: (block
    .
    "{"
    _* @function.inner
    "}")) @function.outer

; constructor without body(metadata)
(constructor_declaration
  _+
  ";") @function.outer

(local_function_statement
  body: (block
    .
    "{"
    _* @function.inner
    "}")) @function.outer

(local_function_statement
  body: (arrow_expression_clause
    "=>"
    _+ @function.inner)) @function.outer

(anonymous_method_expression
  (block
    .
    "{"
    _* @function.inner
    "}")) @function.outer

(lambda_expression
  body: (block
    .
    "{"
    _+ @function.inner
    "}")) @function.outer
