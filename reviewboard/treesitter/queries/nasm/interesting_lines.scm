; adapted from https://github.com/naclsn/tree-sitter-nasm/blob/main/queries/textobjects.scm
(preproc_multiline_macro
  body: (body) @function.inner) @function.outer

(struc_declaration
  body: (struc_declaration_body) @class.inner) @class.outer

(struc_instance
  body: (struc_instance_body) @class.inner) @class.outer
