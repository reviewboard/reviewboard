; Class Objects (Modules, Protocols)
; multiple children
(call
  target: ((identifier) @_identifier
    (#any-of? @_identifier "defmodule" "defprotocol" "defimpl"))
  (arguments
    (alias))
  (do_block
    "do"
    _+ @class.inner
    "end")) @class.outer

; single child match
(call
  target: ((identifier) @_identifier
    (#any-of? @_identifier "defmodule" "defprotocol" "defimpl"))
  (arguments
    (alias))
  (do_block
    "do"
    .
    (_) @class.inner
    .
    "end")) @class.outer

; Function, Parameter, and Call Objects
(anonymous_function
  (stab_clause
    right: (body) @function.inner)) @function.outer

(call
  target: ((identifier) @_identifier
    (#any-of? @_identifier "def" "defmacro" "defmacrop" "defn" "defnp" "defp"))
  (arguments
    [
      (call
        [
          (arguments
            (_) @parameter.inner @parameter.outer
            .
            "," @parameter.outer)
          (arguments
            ((_) @parameter.inner @parameter.outer) @parameter.outer .)
        ])
      (binary_operator
        left: (call
          [
            (arguments
              (_) @parameter.inner @parameter.outer
              .
              "," @parameter.outer)
            (arguments
              ((_) @parameter.inner @parameter.outer) @parameter.outer .)
          ]))
    ])
  [
    (do_block
      "do"
      _+ @function.inner
      "end")
    (do_block
      "do"
      .
      ((_) @function.inner) @function.inner
      .
      "end")
  ]) @function.outer

(call
  target: ((identifier) @_identifier
    (#any-of? @_identifier "def" "defmacro" "defmacrop" "defn" "defnp" "defp"))
  (arguments
    [
      (identifier)
      (binary_operator
        (identifier))
    ])
  [
    (do_block
      "do"
      _+ @function.inner
      "end")
    (do_block
      "do"
      .
      ((_) @function.inner) @function.inner
      .
      "end")
  ]) @function.outer

(call
  target: ((identifier) @_identifier
    (#any-of? @_identifier "def" "defmacro" "defmacrop" "defn" "defnp" "defp"))
  (arguments
    [
      (call
        [
          (arguments
            (_) @parameter.inner @parameter.outer
            .
            "," @parameter.outer)
          (arguments
            ((_) @parameter.inner @parameter.outer) @parameter.outer .)
        ])
      (binary_operator
        left: (call
          [
            (arguments
              (_) @parameter.inner @parameter.outer
              .
              "," @parameter.outer)
            (arguments
              ((_) @parameter.inner @parameter.outer) @parameter.outer .)
          ]))
    ]
    (keywords
      (pair
        value: (_) @function.inner)))) @function.outer

(call
  target: ((identifier) @_identifier
    (#any-of? @_identifier "def" "defmacro" "defmacrop" "defn" "defnp" "defp"))
  (arguments
    [
      (identifier)
      (binary_operator
        (identifier))
    ]
    (keywords
      (pair
        value: (_) @function.inner)))) @function.outer
