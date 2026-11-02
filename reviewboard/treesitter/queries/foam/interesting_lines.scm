(dict) @class.outer

(key_value
  value: _? @function.inner
  (_)* @function.inner
  _? @parameter.inner @function.inner) @function.outer

(code
  (_)* @class.inner) @class.outer
