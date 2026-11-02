(function_declaration
  (function_body_declaration
    (tf_port_list)
    .
    _+ @function.inner
    .
    "endfunction")) @function.outer

(task_declaration
  (task_body_declaration
    (tf_port_list)
    .
    _+ @function.inner
    .
    "endtask")) @function.outer
