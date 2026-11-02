; injections.scm — tree-sitter-postgres language injection queries
;
; Dollar-quoted function bodies in CREATE FUNCTION / CREATE PROCEDURE
; are injected as plpgsql or postgres depending on the LANGUAGE clause.
;
; The createfunc_opt_list is left-recursive, so the LANGUAGE and AS items
; may be at varying nesting depths depending on how many options appear.
; Patterns cover 2..7 createfunc_opt_items in both orderings,
; which handles all practical CREATE FUNCTION statements.
;
; GENERATED FILE — DO NOT EDIT MANUALLY.
; Regenerate with: node script/generate-injections.js

; ============================================================
; PL/pgSQL injection
; ============================================================

; 2 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_item
          (kw_language)
          (NonReservedWord_or_Sconst
            (NonReservedWord
              (identifier) @_lang))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 2 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_item
          (func_as
            (Sconst
              (dollar_quoted_string) @injection.content))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (identifier) @_lang))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 3 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_item
            (kw_language)
            (NonReservedWord_or_Sconst
              (NonReservedWord
                (identifier) @_lang)))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 3 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_item
            (func_as
              (Sconst
                (dollar_quoted_string) @injection.content)))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (identifier) @_lang))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 4 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_item
              (kw_language)
              (NonReservedWord_or_Sconst
                (NonReservedWord
                  (identifier) @_lang))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 4 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_item
              (func_as
                (Sconst
                  (dollar_quoted_string) @injection.content))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (identifier) @_lang))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 5 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_item
                (kw_language)
                (NonReservedWord_or_Sconst
                  (NonReservedWord
                    (identifier) @_lang)))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 5 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_item
                (func_as
                  (Sconst
                    (dollar_quoted_string) @injection.content)))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (identifier) @_lang))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 6 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_item
                  (kw_language)
                  (NonReservedWord_or_Sconst
                    (NonReservedWord
                      (identifier) @_lang))))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 6 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_item
                  (func_as
                    (Sconst
                      (dollar_quoted_string) @injection.content))))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (identifier) @_lang))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 7 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_list
                  (createfunc_opt_item
                    (kw_language)
                    (NonReservedWord_or_Sconst
                      (NonReservedWord
                        (identifier) @_lang)))))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; 7 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_list
                  (createfunc_opt_item
                    (func_as
                      (Sconst
                        (dollar_quoted_string) @injection.content)))))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (identifier) @_lang))))))
 (#match? @_lang "(?i)^plpgsql$")
 (#set! injection.language "plpgsql")
 (#set! injection.include-children))

; ============================================================
; SQL injection (postgres self-injection)
; ============================================================

; 2 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_item
          (kw_language)
          (NonReservedWord_or_Sconst
            (NonReservedWord
              (unreserved_keyword
                (kw_sql))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 2 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_item
          (func_as
            (Sconst
              (dollar_quoted_string) @injection.content))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (unreserved_keyword
              (kw_sql))))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 3 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_item
            (kw_language)
            (NonReservedWord_or_Sconst
              (NonReservedWord
                (unreserved_keyword
                  (kw_sql)))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 3 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_item
            (func_as
              (Sconst
                (dollar_quoted_string) @injection.content)))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (unreserved_keyword
              (kw_sql))))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 4 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_item
              (kw_language)
              (NonReservedWord_or_Sconst
                (NonReservedWord
                  (unreserved_keyword
                    (kw_sql))))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 4 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_item
              (func_as
                (Sconst
                  (dollar_quoted_string) @injection.content))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (unreserved_keyword
              (kw_sql))))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 5 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_item
                (kw_language)
                (NonReservedWord_or_Sconst
                  (NonReservedWord
                    (unreserved_keyword
                      (kw_sql)))))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 5 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_item
                (func_as
                  (Sconst
                    (dollar_quoted_string) @injection.content)))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (unreserved_keyword
              (kw_sql))))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 6 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_item
                  (kw_language)
                  (NonReservedWord_or_Sconst
                    (NonReservedWord
                      (unreserved_keyword
                        (kw_sql))))))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 6 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_item
                  (func_as
                    (Sconst
                      (dollar_quoted_string) @injection.content))))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (unreserved_keyword
              (kw_sql))))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 7 options: LANGUAGE deeper, AS rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_list
                  (createfunc_opt_item
                    (kw_language)
                    (NonReservedWord_or_Sconst
                      (NonReservedWord
                        (unreserved_keyword
                          (kw_sql)))))))))))
      (createfunc_opt_item
        (func_as
          (Sconst
            (dollar_quoted_string) @injection.content))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))

; 7 options: AS deeper, LANGUAGE rightmost
((CreateFunctionStmt
  (opt_createfunc_opt_list
    (createfunc_opt_list
      (createfunc_opt_list
        (createfunc_opt_list
          (createfunc_opt_list
            (createfunc_opt_list
              (createfunc_opt_list
                (createfunc_opt_list
                  (createfunc_opt_item
                    (func_as
                      (Sconst
                        (dollar_quoted_string) @injection.content)))))))))
      (createfunc_opt_item
        (kw_language)
        (NonReservedWord_or_Sconst
          (NonReservedWord
            (unreserved_keyword
              (kw_sql))))))))
 (#set! injection.language "sql")
 (#set! injection.include-children))
