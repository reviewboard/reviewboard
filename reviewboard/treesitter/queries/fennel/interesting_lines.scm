; functions
((fn . name: (_)? . (parameters) . docstring: (_)? . (_) @_start . (_)* . (_)? @_end .)
 (#make-range! "function.inner" @_start @_end)) @function.outer

((lambda . name: (_)? . (parameters) . docstring: (_)? . (_) @_start . (_)* . (_)? @_end .)
 (#make-range! "function.inner" @_start @_end)) @function.outer

(hashfn ["#" "hashfn"] @function.outer.start (_) @function.inner) @function.outer
