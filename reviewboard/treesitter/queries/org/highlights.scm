; A Note on anonymous nodes (represented in a query file as strings). As of
; right now, anonymous nodes can not be anchored.
; See https://github.com/tree-sitter/tree-sitter/issues/1461

; Example highlighting for headlines. The headlines here will be matched
; cyclically, easily extended to match however your heart desires.
(headline (stars) @OrgStars1 (#match? @OrgStars1 "^(\\*{3})*\\*$") (item) @OrgHeadlineLevel1)
(headline (stars) @OrgStars2 (#match? @OrgStars2 "^(\\*{3})*\\*\\*$") (item) @OrgHeadlineLevel2)
(headline (stars) @OrgStars3 (#match? @OrgStars3 "^(\\*{3})*\\*\\*\\*$") (item) @OrgHeadlineLevel3)

; This one should be generated after scanning for configuration, using 
; something like #any-of? for keywords, but could use a match if allowing
; markup on todo keywords is desirable.
(item . (expr) @OrgKeywordTodo (#eq? @OrgKeywordTodo "TODO"))
(item . (expr) @OrgKeywordDone (#eq? @OrgKeywordDone "DONE"))

; Not sure about this one with the anchors.
(item . (expr)? . (expr "[" "#" @OrgPriority [ "num" "str" ] @OrgPriority "]") @OrgPriorityCookie (#match? @OrgPriorityCookie "\[#.\]"))

; Match cookies in a headline or listitem. If you want the numbers
; differently highlighted from the borders, add a capture name to "num".
; ([ (item) (itemtext) ] (expr "[" "num"? @OrgCookieNum "/" "num"? @OrgCookieNum "]" ) @OrgProgressCookie (#match? @OrgProgressCookie "^\[\d*/\d*\]$"))
; ([ (item) (itemtext) ] (expr "[" "num"? @OrgCookieNum "%" "]" ) @OrgPercentCookie (#match? @OrgPercentCookie "^\[\d*%\]$"))

(tag_list (tag) @OrgTag) @OrgTagList

(property_drawer) @OrgPropertyDrawer

; Properties are :name: vale, so to color the ':' we can either add them
; directly, or highlight the property separately from the name and value. If
; priorities are set properly, it should be simple to achieve.
(property name: (expr) @OrgPropertyName (value)? @OrgPropertyValue) @OrgProperty

; Simple examples, but can also match (day), (date), (time), etc.
(timestamp "[") @OrgTimestampInactive
(timestamp "<"
 (day)? @OrgTimestampDay
 (date)? @OrgTimestampDate
 (time)? @OrgTimestampTime
 (repeat)? @OrgTimestampRepeat
 (delay)? @OrgTimestampDelay
 ) @OrgTimestampActive

; Like OrgProperty, easy to choose how the '[fn:LABEL] DESCRIPTION' are highlighted
(fndef label: (expr) @OrgFootnoteLabel (description) @OrgFootnoteDescription) @OrgFootnoteDefinition

; Again like OrgProperty to change the styling of '#+' and ':'. Note that they
; can also be added in the query directly as anonymous nodes to style differently.
(directive name: (expr) @OrgDirectiveName (value)? @OrgDirectiveValue) @OrgDirective

(comment) @OrgComment

; At the moment, these three elements use one regex for the whole name.
; So (name) -> :name:, ideally this will not be the case, so it follows the
; patterns listed above, but that's the current status. Conflict issues.
(drawer name: (expr) @OrgDrawerName (contents)? @OrgDrawerContents) @OrgDrawer
(block name: (expr) @OrgBlockName (contents)? @OrgBlockContents) @OrgBlock
(dynamic_block name: (expr) @OrgDynamicBlockName (contents)? @OrgDynamicBlockContents) @OrgDynamicBlock

; Can match different styles with a (#match?) or (#eq?) predicate if desired
(bullet) @OrgListBullet

; Get different colors for different statuses as follows
(checkbox) @OrgCheckbox
(checkbox status: (expr "-") @OrgCheckInProgress)
(checkbox status: (expr "str") @OrgCheckDone (#any-of? @OrgCheckDone "x" "X"))
(checkbox status: (expr) @Error (#not-any-of? @Error "x" "X" "-"))

; If you want the ruler one color and the separators a different color,
; something like this would do it:
; (hr "|" @OrgTableHRBar) @OrgTableHorizontalRuler
(hr) @OrgTableHorizontalRuler

; Can do all sorts of fun highlighting here..
(cell (contents . (expr "=")) @OrgCellFormula (#match? @OrgCellFormula "^\d+([.,]\d+)*$"))

; Dollars, floats, etc. Strings.. all options to play with
(cell (contents . (expr "num") @OrgCellNumber (#match? @OrgCellNumber "^\d+([.,]\d+)*$") .))
