    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "url(#mysym)" ],
    invalid_values: []
  },
  "marker-start": {
    domProp: "markerStart",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "url(#mysym)" ],
    invalid_values: []
  },
  "mask": {
    domProp: "mask",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    /* FIXME: All mask-border-* should be added when we implement them. */
    subproperties: ["mask-clip", "mask-image", "mask-mode", "mask-origin", "mask-position", "mask-repeat", "mask-size" , "mask-composite"],
    initial_values: [ "match-source", "none", "repeat", "add", "0% 0%", "top left", "left top", "0% 0% / auto", "top left / auto", "left top / auto", "0% 0% / auto auto",
      "top left none", "left top none", "none left top", "none top left", "none 0% 0%", "left top / auto none", "left top / auto auto none",
      "match-source none repeat add top left", "left top repeat none add", "none repeat add top left / auto", "left top / auto repeat none add match-source", "none repeat add 0% 0% / auto auto match-source" ],
                      "repeat-x repeat-y",
                      "repeat repeat-x",
                      "repeat repeat-y",
                      "repeat-x repeat",
                      "repeat-y repeat" ]
  },
  "mask-size": {
    domProp: "maskSize",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto", "auto auto" ],
    other_values: [ "contain", "cover", "100px auto", "auto 100px", "100% auto", "auto 100%", "25% 50px", "3em 40%",
      "calc(20px)",
      "calc(20px) 10px",
      "10px calc(20px)",
      "calc(20px) 25%",
      "25% calc(20px)",
      "calc(20px) calc(20px)",
      "calc(20px + 1em) calc(20px / 2)",
      "calc(20px + 50%) calc(50% - 10px)",
      "calc(-20px) calc(-50%)",
      "calc(-20%) calc(-50%)"
    ],
    invalid_values: [ "contain contain", "cover cover", "cover auto", "auto cover", "contain cover", "cover contain", "-5px 3px", "3px -5px", "auto -5px", "-5px auto", "5 3", "10px calc(10px + rubbish)" ]
  },
  "shape-rendering": {
    domProp: "shapeRendering",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: [ "optimizeSpeed", "crispEdges", "geometricPrecision" ],
    invalid_values: []
  },
  "stop-color": {
    domProp: "stopColor",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    prerequisites: { "color": "blue" },
    initial_values: [ "black", "#000", "#000000", "rgb(0,0,0)", "rgba(0,0,0,1)" ],
    other_values: [ "green", "#fc3", "currentColor" ],
    invalid_values: [ "url('#myserver')", "url(foo.svg#myserver)", 'url("#myserver") green', "000000", "ff00ff" ]
  },
  "stop-opacity": {
    domProp: "stopOpacity",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "1", "2.8", "1.000" ],
    other_values: [ "0", "0.3", "-7.3" ],
    invalid_values: []
  },
  "stroke": {
    domProp: "stroke",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "black", "#000", "#000000", "rgb(0,0,0)", "rgba(0,0,0,1)", "green", "#fc3", "url('#myserver')", "url(foo.svg#myserver)", 'url("#myserver") green', "currentColor", "context-fill", "context-stroke" ],
    invalid_values: [ "000000", "ff00ff" ]
  },
  "stroke-dasharray": {
    domProp: "strokeDasharray",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none", "context-value" ],
    other_values: [ "5px,3px,2px", "5px 3px 2px", "  5px ,3px\t, 2px ", "1px", "5%", "3em" ],
    invalid_values: [ "-5px,3px,2px", "5px,3px,-2px" ]
  },
  "stroke-dashoffset": {
    domProp: "strokeDashoffset",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "0", "-0px", "0em", "context-value" ],
    other_values: [ "3px", "3%", "1em" ],
    invalid_values: []
  },
  "stroke-linecap": {
    domProp: "strokeLinecap",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "butt" ],
    other_values: [ "round", "square" ],
    invalid_values: []
  },
  "stroke-linejoin": {
    domProp: "strokeLinejoin",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "miter" ],
    other_values: [ "round", "bevel" ],
    invalid_values: []
  },
  "stroke-miterlimit": {
    domProp: "strokeMiterlimit",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "4" ],
    other_values: [ "1", "7", "5000", "1.1" ],
    invalid_values: [ "0.9", "0", "-1", "3px", "-0.3" ]
  },
  "stroke-opacity": {
    domProp: "strokeOpacity",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "1", "2.8", "1.000", "context-fill-opacity", "context-stroke-opacity" ],
    other_values: [ "0", "0.3", "-7.3" ],
    invalid_values: []
  },
  "stroke-width": {
    domProp: "strokeWidth",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "1px", "context-value" ],
    other_values: [ "0", "0px", "-0em", "17px", "0.2em" ],
    invalid_values: [ "-0.1px", "-3px" ]
  },
  "text-anchor": {
    domProp: "textAnchor",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "start" ],
    other_values: [ "middle", "end" ],
    invalid_values: []
  },
  "text-rendering": {
    domProp: "textRendering",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: [ "optimizeSpeed", "optimizeLegibility", "geometricPrecision" ],
    invalid_values: []
  },
  "vector-effect": {
    domProp: "vectorEffect",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "non-scaling-stroke" ],
    invalid_values: []
  },
  "-moz-window-dragging": {
    domProp: "MozWindowDragging",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "default" ],
    other_values: [ "drag", "no-drag" ],
    invalid_values: [ "none" ]
  },
  "align-content": {
    domProp: "alignContent",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "normal" ],
    other_values: [ "start", "end", "flex-start", "flex-end", "center", "left",
                    "right", "space-between", "space-around", "space-evenly",
                    "baseline", "last-baseline", "stretch", "start safe",
                    "unsafe end", "unsafe end stretch", "end safe space-evenly" ],
    invalid_values: [ "none", "5", "self-end", "safe", "normal unsafe", "unsafe safe",
                      "safe baseline", "baseline unsafe", "baseline end", "end normal",
                      "safe end unsafe start", "safe end unsafe", "normal safe start",
                      "unsafe end start", "end start safe", "space-between unsafe",
                      "stretch safe", "auto" ]
  },
  "align-items": {
    domProp: "alignItems",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "normal" ],
    // Can't test 'left'/'right' here since that computes to 'start' for blocks.
    other_values: [ "end", "flex-start", "flex-end", "self-start", "self-end",
                    "center", "stretch", "baseline", "unsafe left", "start",
                    "center unsafe", "safe right", "center safe" ],
    invalid_values: [ "space-between", "abc", "5%", "legacy", "legacy end",
                      "end legacy", "unsafe", "unsafe baseline", "normal unsafe",
                      "safe left unsafe", "safe stretch", "end end", "auto" ]
  },
  "align-self": {
    domProp: "alignSelf",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    // (Assuming defaults on the parent, 'auto' will compute to 'normal'.)
    initial_values: [ "auto", "normal" ],
    other_values: [ "start", "flex-start", "flex-end", "center", "stretch",
                    "baseline", "last-baseline", "right safe", "unsafe center",
                    "self-start", "self-end safe" ],
    invalid_values: [ "space-between", "abc", "30px", "stretch safe", "safe" ]
  },
  "justify-content": {
    domProp: "justifyContent",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "normal" ],
    other_values: [ "start", "end", "flex-start", "flex-end", "center", "left",
                    "right", "space-between", "space-around", "space-evenly",
                    "baseline", "last-baseline", "stretch", "start safe",
                    "unsafe end", "unsafe end stretch", "end safe space-evenly" ],
    invalid_values: [ "30px", "5%", "self-end", "safe", "normal unsafe", "unsafe safe",
                      "safe baseline", "baseline unsafe", "baseline end", "normal end",
                      "safe end unsafe start", "safe end unsafe", "normal safe start",
                      "unsafe end start", "end start safe", "space-around unsafe",
                      "safe stretch", "auto" ]
  },
  "justify-items": {
    domProp: "justifyItems",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto", "normal" ],
    other_values: [ "end", "flex-start", "flex-end", "self-start", "self-end",
                    "center", "left", "right", "baseline", "stretch", "start",
                    "legacy left", "right legacy", "legacy center",
                    "unsafe right", "left unsafe", "safe right", "center safe" ],
    invalid_values: [ "space-between", "abc", "30px", "legacy", "legacy start",
                      "end legacy", "legacy baseline", "legacy legacy", "unsafe",
                      "safe legacy left", "legacy left safe", "legacy safe left",
                      "safe left legacy", "legacy left legacy", "baseline unsafe",
                      "safe unsafe", "safe left unsafe", "safe stretch" ]
  },
  "justify-self": {
    domProp: "justifySelf",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto", "normal" ],
    other_values: [ "start", "end", "flex-start", "flex-end", "self-start",
                    "self-end", "center", "left", "right", "baseline",
                    "last-baseline", "stretch", "left unsafe", "unsafe right",
                    "safe right", "center safe" ],
    invalid_values: [ "space-between", "abc", "30px", "none",
                      "legacy left", "right legacy" ]
  },
  "flex": {
    domProp: "flex",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "flex-grow",
      "flex-shrink",
      "flex-basis"
    ],
    initial_values: [ "0 1 auto", "auto 0 1", "0 auto", "auto 0" ],
    other_values: [
      "none",
      "1",
      "0",
      "0 1",
      "0.5",
      "1.2 3.4",
      "0 0 0",
      "0 0 0px",
      "0px 0 0",
      "5px 0 0",
      "2 auto",
      "auto 4",
      "auto 5.6 7.8",
      "-moz-max-content",
      "1 -moz-max-content",
      "1 2 -moz-max-content",
      "-moz-max-content 1",
      "-moz-max-content 1 2",
      "-0"
    ],
    invalid_values: [
      "1 2px 3",
      "1 auto 3",
      "1px 2 3px",
      "1px 2 3 4px",
      "-1",
      "1 -1",
      "0 1 calc(0px + rubbish)",
    ]
  },
  "flex-basis": {
    domProp: "flexBasis",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ " auto" ],
        // NOTE: This is cribbed directly from the "width" chunk, since this
        // property takes the exact same values as width (albeit with
        // different semantics on 'auto').
        // XXXdholbert (Maybe these should get separated out into
        // a reusable array defined at the top of this file?)
    other_values: [ "15px", "3em", "15%", "-moz-max-content", "-moz-min-content", "-moz-fit-content", "-moz-available",
      // valid calc() values
      "calc(-2px)",
      "calc(2px)",
      "calc(50%)",
      "calc(50% + 2px)",
      "calc( 50% + 2px)",
      "calc(50% + 2px )",
      "calc( 50% + 2px )",
      "calc(50% - -2px)",
      "calc(2px - -50%)",
      "calc(3*25px)",
      "calc(3 *25px)",
      "calc(3 * 25px)",
      "calc(3* 25px)",
      "calc(25px*3)",
      "calc(25px *3)",
      "calc(25px* 3)",
      "calc(25px * 3)",
      "calc(3*25px + 50%)",
      "calc(50% - 3em + 2px)",
      "calc(50% - (3em + 2px))",
      "calc((50% - 3em) + 2px)",
      "calc(2em)",
      "calc(50%)",
      "calc(50px/2)",
      "calc(50px/(2 - 1))"
    ],
    invalid_values: [ "none", "-2px",
      // invalid calc() values
      "calc(50%+ 2px)",
      "calc(50% +2px)",
      "calc(50%+2px)",
      "-moz-min()",
      "calc(min())",
      "-moz-max()",
      "calc(max())",
      "-moz-min(5px)",
      "calc(min(5px))",
      "-moz-max(5px)",
      "calc(max(5px))",
      "-moz-min(5px,2em)",
      "calc(min(5px,2em))",
      "-moz-max(5px,2em)",
      "calc(max(5px,2em))",
      "calc(50px/(2 - 2))",
      // If we ever support division by values, which is
      // complicated for the reasons described in
      // http://lists.w3.org/Archives/Public/www-style/2010Jan/0007.html
      // , we should support all 4 of these as described in
      // http://lists.w3.org/Archives/Public/www-style/2009Dec/0296.html
      "calc((3em / 100%) * 3em)",
      "calc(3em / 100% * 3em)",
      "calc(3em * (3em / 100%))",
      "calc(3em * 3em / 100%)"
    ]
  },
  "flex-direction": {
    domProp: "flexDirection",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "row" ],
    other_values: [ "row-reverse", "column", "column-reverse" ],
    invalid_values: [ "10px", "30%", "justify", "column wrap" ]
  },
  "flex-flow": {
    domProp: "flexFlow",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "flex-direction",
      "flex-wrap"
    ],
    initial_values: [ "row nowrap", "nowrap row", "row", "nowrap" ],
    other_values: [
      // only specifying one property:
      "column",
      "wrap",
      "wrap-reverse",
      // specifying both properties, 'flex-direction' first:
      "row wrap",
      "row wrap-reverse",
      "column wrap",
      "column wrap-reverse",
      // specifying both properties, 'flex-wrap' first:
      "wrap row",
      "wrap column",
      "wrap-reverse row",
      "wrap-reverse column",
    ],
    invalid_values: [
      // specifying flex-direction twice (invalid):
      "row column",
      "row column nowrap",
      "row nowrap column",
      "nowrap row column",
      // specifying flex-wrap twice (invalid):
      "nowrap wrap-reverse",
      "nowrap wrap-reverse row",
      "nowrap row wrap-reverse",
      "row nowrap wrap-reverse",
      // Invalid data-type / invalid keyword type:
      "1px", "5%", "justify", "none"
    ]
  },
  "flex-grow": {
    domProp: "flexGrow",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "0" ],
    other_values: [ "3", "1", "1.0", "2.5", "123" ],
    invalid_values: [ "0px", "-5", "1%", "3em", "stretch", "auto" ]
  },
  "flex-shrink": {
    domProp: "flexShrink",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "1" ],
    other_values: [ "3", "0", "0.0", "2.5", "123" ],
    invalid_values: [ "0px", "-5", "1%", "3em", "stretch", "auto" ]
  },
  "flex-wrap": {
    domProp: "flexWrap",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "nowrap" ],
    other_values: [ "wrap", "wrap-reverse" ],
    invalid_values: [ "10px", "30%", "justify", "column wrap", "auto" ]
  },
  "order": {
    domProp: "order",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "0" ],
    other_values: [ "1", "99999", "-1", "-50" ],
    invalid_values: [ "0px", "1.0", "1.", "1%", "0.2", "3em", "stretch" ]
  },

  // Aliases
  "-moz-transform": {
    domProp: "MozTransform",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transform",
    subproperties: [ "transform" ],
    // NOTE: We specify other_values & invalid_values explicitly here (instead
    // of deferring to "transform") because we accept some legacy syntax as
    // valid for "-moz-transform" but not for "transform".
    other_values: [ "translatex(1px)", "translatex(4em)",
      "translatex(-4px)", "translatex(3px)",
      "translatex(0px) translatex(1px) translatex(2px) translatex(3px) translatex(4px)",
      "translatey(4em)", "translate(3px)", "translate(10px, -3px)",
      "rotate(45deg)", "rotate(45grad)", "rotate(45rad)",
      "rotate(0.25turn)", "rotate(0)", "scalex(10)", "scaley(10)",
      "scale(10)", "scale(10, 20)", "skewx(30deg)", "skewx(0)",
      "skewy(0)", "skewx(30grad)", "skewx(30rad)", "skewx(0.08turn)",
      "skewy(30deg)", "skewy(30grad)", "skewy(30rad)", "skewy(0.08turn)",
      "rotate(45deg) scale(2, 1)", "skewx(45deg) skewx(-50grad)",
      "translate(0, 0) scale(1, 1) skewx(0) skewy(0) matrix(1, 0, 0, 1, 0, 0)",
      "translatex(50%)", "translatey(50%)", "translate(50%)",
      "translate(3%, 5px)", "translate(5px, 3%)",
      "matrix(1, 2, 3, 4, 5, 6)",
      /* valid calc() values */
      "translatex(calc(5px + 10%))",
      "translatey(calc(0.25 * 5px + 10% / 3))",
      "translate(calc(5px - 10% * 3))",
      "translate(calc(5px - 3 * 10%), 50px)",
      "translate(-50px, calc(5px - 10% * 3))",
      /* valid only when prefixed */
      "matrix(1, 2, 3, 4, 5px, 6%)",
      "matrix(1, 2, 3, 4, 5%, 6px)",
      "matrix(1, 2, 3, 4, 5%, 6%)",
      "matrix(1, 2, 3, 4, 5px, 6em)",
      "matrix(1, 0, 0, 1, calc(5px * 3), calc(10% - 3px))",
      "translatez(1px)", "translatez(4em)", "translatez(-4px)",
      "translatez(0px)", "translatez(2px) translatez(5px)",
      "translate3d(3px, 4px, 5px)", "translate3d(2em, 3px, 1em)",
      "translatex(2px) translate3d(4px, 5px, 6px) translatey(1px)",
      "scale3d(4, 4, 4)", "scale3d(-2, 3, -7)", "scalez(4)",
      "scalez(-6)", "rotate3d(2, 3, 4, 45deg)",
      "rotate3d(-3, 7, 0, 12rad)", "rotatex(15deg)", "rotatey(-12grad)",
      "rotatez(72rad)", "rotatex(0.125turn)", "perspective(1000px)",
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)",
      /* valid only when prefixed */
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13px, 14em, 15px, 16)",
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20%, 10%, 15, 16)",
    ],
    invalid_values: ["1px", "#0000ff", "red", "auto",
      "translatex(1)", "translatey(1)", "translate(2)",
      "translate(-3, -4)",
      "translatex(1px 1px)", "translatex(translatex(1px))",
      "translatex(#0000ff)", "translatex(red)", "translatey()",
      "matrix(1px, 2px, 3px, 4px, 5px, 6px)", "scale(150%)",
      "skewx(red)", "matrix(1%, 0, 0, 0, 0px, 0px)",
      "matrix(0, 1%, 2, 3, 4px,5px)", "matrix(0, 1, 2%, 3, 4px, 5px)",
      "matrix(0, 1, 2, 3%, 4%, 5%)",
      /* invalid calc() values */
      "translatey(-moz-min(5px,10%))",
      "translatex(-moz-max(5px,10%))",
      "translate(10px, calc(min(5px,10%)))",
      "translate(calc(max(5px,10%)), 10%)",
      "matrix(1, 0, 0, 1, max(5px * 3), calc(10% - 3px))",
      "perspective(0px)", "perspective(-10px)", "matrix3d(dinosaur)",
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17)",
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)",
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15%, 16)",
      "matrix3d(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16px)",
      "rotatey(words)", "rotatex(7)", "translate3d(3px, 4px, 1px, 7px)",
    ],
  },
  "-moz-transform-origin": {
    domProp: "MozTransformOrigin",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transform-origin",
    subproperties: [ "transform-origin" ],
  },
  "-moz-perspective-origin": {
    domProp: "MozPerspectiveOrigin",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "perspective-origin",
    subproperties: [ "perspective-origin" ],
  },
  "-moz-perspective": {
    domProp: "MozPerspective",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "perspective",
    subproperties: [ "perspective" ],
  },
  "-moz-backface-visibility": {
    domProp: "MozBackfaceVisibility",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "backface-visibility",
    subproperties: [ "backface-visibility" ],
  },
  "-moz-transform-style": {
    domProp: "MozTransformStyle",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transform-style",
    subproperties: [ "transform-style" ],
  },
  "-moz-border-image": {
    domProp: "MozBorderImage",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    alias_for: "border-image",
    subproperties: [ "border-image-source", "border-image-slice", "border-image-width", "border-image-outset", "border-image-repeat" ],
  },
  "-moz-transition": {
    domProp: "MozTransition",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    alias_for: "transition",
    subproperties: [ "transition-property", "transition-duration", "transition-timing-function", "transition-delay" ],
  },
  "-moz-transition-delay": {
    domProp: "MozTransitionDelay",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transition-delay",
    subproperties: [ "transition-delay" ],
  },
  "-moz-transition-duration": {
    domProp: "MozTransitionDuration",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transition-duration",
    subproperties: [ "transition-duration" ],
  },
  "-moz-transition-property": {
    domProp: "MozTransitionProperty",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transition-property",
    subproperties: [ "transition-property" ],
  },
  "-moz-transition-timing-function": {
    domProp: "MozTransitionTimingFunction",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "transition-timing-function",
    subproperties: [ "transition-timing-function" ],
  },
  "-moz-animation": {
    domProp: "MozAnimation",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    alias_for: "animation",
    subproperties: [ "animation-name", "animation-duration", "animation-timing-function", "animation-delay", "animation-direction", "animation-fill-mode", "animation-iteration-count", "animation-play-state" ],
  },
  "-moz-animation-delay": {
    domProp: "MozAnimationDelay",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-delay",
    subproperties: [ "animation-delay" ],
  },
  "-moz-animation-direction": {
    domProp: "MozAnimationDirection",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-direction",
    subproperties: [ "animation-direction" ],
  },
  "-moz-animation-duration": {
    domProp: "MozAnimationDuration",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-duration",
    subproperties: [ "animation-duration" ],
  },
  "-moz-animation-fill-mode": {
    domProp: "MozAnimationFillMode",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-fill-mode",
    subproperties: [ "animation-fill-mode" ],
  },
  "-moz-animation-iteration-count": {
    domProp: "MozAnimationIterationCount",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-iteration-count",
    subproperties: [ "animation-iteration-count" ],
  },
  "-moz-animation-name": {
    domProp: "MozAnimationName",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-name",
    subproperties: [ "animation-name" ],
  },
  "-moz-animation-play-state": {
    domProp: "MozAnimationPlayState",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-play-state",
    subproperties: [ "animation-play-state" ],
  },
  "-moz-animation-timing-function": {
    domProp: "MozAnimationTimingFunction",
    inherited: false,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "animation-timing-function",
    subproperties: [ "animation-timing-function" ],
  },
  "-moz-font-feature-settings": {
    domProp: "MozFontFeatureSettings",
    inherited: true,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "font-feature-settings",
    subproperties: [ "font-feature-settings" ],
  },
  "-moz-font-language-override": {
    domProp: "MozFontLanguageOverride",
    inherited: true,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "font-language-override",
    subproperties: [ "font-language-override" ],
  },
  "-moz-hyphens": {
    domProp: "MozHyphens",
    inherited: true,
    type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
    alias_for: "hyphens",
    subproperties: [ "hyphens" ],
  }
}

function logical_axis_prop_get_computed(cs, property)
{
  // Use defaults for these two properties in case the vertical text
  // pref (which they live behind) is turned off.
  var writingMode = cs.getPropertyValue("writing-mode") || "horizontal-tb";
  var orientation = writingMode.substring(0, writingMode.indexOf("-"));

  var mappings = {
    "block-size":      { horizontal: "height",
                         vertical:   "width",
                         sideways:   "width"      },
    "inline-size":     { horizontal: "width",
                         vertical:   "height",
                         sideways:   "height"     },
    "max-block-size":  { horizontal: "max-height",
                         vertical:   "max-width",
                         sideways:   "max-width"  },
    "max-inline-size": { horizontal: "max-width",
                         vertical:   "max-height",
                         sideways:   "max-height" },
    "min-block-size":  { horizontal: "min-height",
                         vertical:   "min-width",
                         sideways:   "min-width"  },
    "min-inline-size": { horizontal: "min-width",
                         vertical:   "min-height",
                         sideways:   "min-height" },
  };

  if (!mappings[property]) {
    throw "unexpected property " + property;
  }

  var prop = mappings[property][orientation];
  if (!prop) {
    throw "unexpected writing mode " + writingMode;
  }

  return cs.getPropertyValue(prop);
}

function logical_box_prop_get_computed(cs, property)
{
  // http://dev.w3.org/csswg/css-writing-modes-3/#logical-to-physical

  // Use default for writing-mode in case the vertical text
  // pref (which it lives behind) is turned off.
  var writingMode = cs.getPropertyValue("writing-mode") || "horizontal-tb";

  var direction = cs.getPropertyValue("direction");

  // keys in blockMappings are writing-mode values
  var blockMappings = {
    "horizontal-tb": { "start": "top",   "end": "bottom" },
    "vertical-rl":   { "start": "right", "end": "left"   },
    "vertical-lr":   { "start": "left",  "end": "right"  },
    "sideways-rl":   { "start": "right", "end": "left"   },
    "sideways-lr":   { "start": "left",  "end": "right"  },
  };

  // keys in inlineMappings are regular expressions that match against
  // a {writing-mode,direction} pair as a space-separated string
  var inlineMappings = {
    "horizontal-tb ltr": { "start": "left",   "end": "right"  },
    "horizontal-tb rtl": { "start": "right",  "end": "left"   },
    "vertical-.. ltr":   { "start": "bottom", "end": "top"    },
    "vertical-.. rtl":   { "start": "top",    "end": "bottom" },
    "vertical-.. ltr":   { "start": "top",    "end": "bottom" },
    "vertical-.. rtl":   { "start": "bottom", "end": "top"    },
    "sideways-lr ltr":   { "start": "bottom", "end": "top"    },
    "sideways-lr rtl":   { "start": "top",    "end": "bottom" },
    "sideways-rl ltr":   { "start": "top",    "end": "bottom" },
    "sideways-rl rtl":   { "start": "bottom", "end": "top"    },
  };

  var blockMapping = blockMappings[writingMode];
  var inlineMapping;

  // test each regular expression in inlineMappings against the
  // {writing-mode,direction} pair
  var key = `${writingMode} ${direction}`;
  for (var k in inlineMappings) {
    if (new RegExp(k).test(key)) {
      inlineMapping = inlineMappings[k];
      break;
    }
  }

  if (!blockMapping || !inlineMapping) {
    throw "Unexpected writing mode property values";
  }

  function physicalize(aProperty, aMapping, aLogicalPrefix) {
    for (var logicalSide in aMapping) {
      var physicalSide = aMapping[logicalSide];
      logicalSide = aLogicalPrefix + logicalSide;
      aProperty = aProperty.replace(logicalSide, physicalSide);
    }
    return aProperty;
  }

  if (/^-moz-/.test(property)) {
    property = physicalize(property.substring(5), inlineMapping, "");
  } else if (/^offset-(block|inline)-(start|end)/.test(property)) {
    property = property.substring(7);  // we want "top" not "offset-top", e.g.
    property = physicalize(property, blockMapping, "block-");
    property = physicalize(property, inlineMapping, "inline-");
  } else if (/-(block|inline)-(start|end)/.test(property)) {
    property = physicalize(property, blockMapping, "block-");
    property = physicalize(property, inlineMapping, "inline-");
  } else {
    throw "Unexpected property";
  }
  return cs.getPropertyValue(property);
}

// Helper to get computed style of "-webkit-box-orient" from "flex-direction"
// and the "writing-mode".
function webkit_orient_get_computed(cs, property)
{
  var writingMode = cs.getPropertyValue("writing-mode") || "horizontal-tb";

  var mapping; // map from flex-direction values to -webkit-box-orient values.
  if (writingMode == "horizontal-tb") {
    // Horizontal writing-mode
    mapping = { "row" : "horizontal", "column" : "vertical"};
  } else {
    // Vertical writing-mode
    mapping = { "row" : "vertical",   "column" : "horizontal"};
  }

  var flexDirection = cs.getPropertyValue("flex-direction");
  return mapping[flexDirection];
}

// Get the computed value for a property.  For shorthands, return the
// computed values of all the subproperties, delimited by " ; ".
function get_computed_value(cs, property)
{
  var info = gCSSProperties[property];
  if (info.type == CSS_TYPE_TRUE_SHORTHAND ||
      (info.type == CSS_TYPE_SHORTHAND_AND_LONGHAND &&
        (property == "text-decoration" || property == "mask"))) {
    var results = [];
    for (var idx in info.subproperties) {
      var subprop = info.subproperties[idx];
      results.push(get_computed_value(cs, subprop));
    }
    return results.join(" ; ");
  }
  if (info.get_computed)
    return info.get_computed(cs, property);
  return cs.getPropertyValue(property);
}

if (IsCSSPropertyPrefEnabled("layout.css.touch_action.enabled")) {
    gCSSProperties["touch-action"] = {
        domProp: "touchAction",
        inherited: false,
        type: CSS_TYPE_LONGHAND,
        initial_values: ["auto"],
        other_values: ["none", "pan-x", "pan-y", "pan-x pan-y", "pan-y pan-x", "manipulation"],
        invalid_values: ["zoom", "pinch", "tap", "10px", "2", "auto pan-x", "pan-x auto", "none pan-x", "pan-x none",
                 "auto pan-y", "pan-y auto", "none pan-y", "pan-y none", "pan-x pan-x", "pan-y pan-y",
                 "pan-x pan-y none", "pan-x none pan-y", "none pan-x pan-y", "pan-y pan-x none", "pan-y none pan-x", "none pan-y pan-x",
                 "pan-x pan-y auto", "pan-x auto pan-y", "auto pan-x pan-y", "pan-y pan-x auto", "pan-y auto pan-x", "auto pan-y pan-x",
                 "pan-x pan-y zoom", "pan-x zoom pan-y", "zoom pan-x pan-y", "pan-y pan-x zoom", "pan-y zoom pan-x", "zoom pan-y pan-x",
                 "pan-x pan-y pan-x", "pan-x pan-x pan-y", "pan-y pan-x pan-x", "pan-y pan-x pan-y", "pan-y pan-y pan-x", "pan-x pan-y pan-y",
                 "manipulation none", "none manipulation", "manipulation auto", "auto manipulation", "manipulation zoom", "zoom manipulation",
                 "manipulation manipulation", "manipulation pan-x", "pan-x manipulation", "manipulation pan-y", "pan-y manipulation",
                 "manipulation pan-x pan-y", "pan-x manipulation pan-y", "pan-x pan-y manipulation",
                 "manipulation pan-y pan-x", "pan-y manipulation pan-x", "pan-y pan-x manipulation"]
    };
}

if (IsCSSPropertyPrefEnabled("layout.css.vertical-text.enabled")) {
  var verticalTextProperties = {
    "writing-mode": {
      domProp: "writingMode",
      inherited: true,
      type: CSS_TYPE_LONGHAND,
      initial_values: [ "horizontal-tb", "lr", "lr-tb", "rl", "rl-tb" ],
      other_values: [ "vertical-lr", "vertical-rl", "sideways-rl", "sideways-lr", "tb", "tb-rl" ],
      invalid_values: [ "10px", "30%", "justify", "auto", "1em" ]
    },
    "text-orientation": {
      domProp: "textOrientation",
      inherited: true,
      type: CSS_TYPE_LONGHAND,
      initial_values: [ "mixed" ],
      other_values: [ "upright", "sideways", "sideways-right" ], /* sideways-right alias for backward compatibility */
      invalid_values: [ "none", "3em", "sideways-left" ] /* sideways-left removed from CSS Writing Modes */
    },
    "border-block-end": {
      domProp: "borderBlockEnd",
      inherited: false,
      type: CSS_TYPE_TRUE_SHORTHAND,
      subproperties: [ "border-block-end-color", "border-block-end-style", "border-block-end-width" ],
      initial_values: [ "none", "medium", "currentColor", "thin", "none medium currentcolor" ],
      other_values: [ "solid", "green", "medium solid", "green solid", "10px solid", "thick solid", "5px green none" ],
      invalid_values: [ "5%", "5", "5 solid green" ]
    },
    "block-size": {
      domProp: "blockSize",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      axis: true,
      get_computed: logical_axis_prop_get_computed,
      /* XXX testing auto has prerequisites */
      initial_values: [ "auto" ],
      prerequisites: { "display": "block" },
      other_values: [ "15px", "3em", "15%",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "none", "-moz-max-content", "-moz-min-content", "-moz-fit-content", "-moz-available" ],
    },
    "border-block-end-color": {
      domProp: "borderBlockEndColor",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      initial_values: [ "currentColor" ],
      other_values: [ "green", "rgba(255,128,0,0.5)", "transparent" ],
      invalid_values: [ "#0", "#00", "#0000", "#00000", "#0000000", "#00000000", "#000000000", "000000" ]
    },
    "border-block-end-style": {
      domProp: "borderBlockEndStyle",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* XXX hidden is sometimes the same as initial */
      initial_values: [ "none" ],
      other_values: [ "solid", "dashed", "dotted", "double", "outset", "inset", "groove", "ridge" ],
      invalid_values: []
    },
    "border-block-end-width": {
      domProp: "borderBlockEndWidth",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      prerequisites: { "border-block-end-style": "solid" },
      initial_values: [ "medium", "3px", "calc(4px - 1px)" ],
      other_values: [ "thin", "thick", "1px", "2em",
        "calc(2px)",
        "calc(-2px)",
        "calc(0em)",
        "calc(0px)",
        "calc(5em)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 5em)",
      ],
      invalid_values: [ "5%", "5" ]
    },
    "border-block-start": {
      domProp: "borderBlockStart",
      inherited: false,
      type: CSS_TYPE_TRUE_SHORTHAND,
      subproperties: [ "border-block-start-color", "border-block-start-style", "border-block-start-width" ],
      initial_values: [ "none", "medium", "currentColor", "thin", "none medium currentcolor" ],
      other_values: [ "solid", "green", "medium solid", "green solid", "10px solid", "thick solid", "5px green none" ],
      invalid_values: [ "5%", "5", "5 solid green" ]
    },
    "border-block-start-color": {
      domProp: "borderBlockStartColor",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      initial_values: [ "currentColor" ],
      other_values: [ "green", "rgba(255,128,0,0.5)", "transparent" ],
      invalid_values: [ "#0", "#00", "#0000", "#00000", "#0000000", "#00000000", "#000000000", "000000" ]
    },
    "border-block-start-style": {
      domProp: "borderBlockStartStyle",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* XXX hidden is sometimes the same as initial */
      initial_values: [ "none" ],
      other_values: [ "solid", "dashed", "dotted", "double", "outset", "inset", "groove", "ridge" ],
      invalid_values: []
    },
    "border-block-start-width": {
      domProp: "borderBlockStartWidth",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      prerequisites: { "border-block-start-style": "solid" },
      initial_values: [ "medium", "3px", "calc(4px - 1px)" ],
      other_values: [ "thin", "thick", "1px", "2em",
        "calc(2px)",
        "calc(-2px)",
        "calc(0em)",
        "calc(0px)",
        "calc(5em)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 5em)",
      ],
      invalid_values: [ "5%", "5" ]
    },
    "-moz-border-end": {
      domProp: "MozBorderEnd",
      inherited: false,
      type: CSS_TYPE_TRUE_SHORTHAND,
      alias_for: "border-inline-end",
      subproperties: [ "-moz-border-end-color", "-moz-border-end-style", "-moz-border-end-width" ],
    },
    "-moz-border-end-color": {
      domProp: "MozBorderEndColor",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "border-inline-end-color",
      subproperties: [ "border-inline-end-color" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-border-end-style": {
      domProp: "MozBorderEndStyle",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "border-inline-end-style",
      subproperties: [ "border-inline-end-style" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-border-end-width": {
      domProp: "MozBorderEndWidth",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "border-inline-end-width",
      subproperties: [ "border-inline-end-width" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-border-start": {
      domProp: "MozBorderStart",
      inherited: false,
      type: CSS_TYPE_TRUE_SHORTHAND,
      alias_for: "border-inline-start",
      subproperties: [ "-moz-border-start-color", "-moz-border-start-style", "-moz-border-start-width" ],
    },
    "-moz-border-start-color": {
      domProp: "MozBorderStartColor",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "border-inline-start-color",
      subproperties: [ "border-inline-start-color" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-border-start-style": {
      domProp: "MozBorderStartStyle",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "border-inline-start-style",
      subproperties: [ "border-inline-start-style" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-border-start-width": {
      domProp: "MozBorderStartWidth",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "border-inline-start-width",
      subproperties: [ "border-inline-start-width" ],
      get_computed: logical_box_prop_get_computed,
    },
    "inline-size": {
      domProp: "inlineSize",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      axis: true,
      get_computed: logical_axis_prop_get_computed,
      /* XXX testing auto has prerequisites */
      initial_values: [ "auto" ],
      prerequisites: { "display": "block" },
      other_values: [ "15px", "3em", "15%",
        // these three keywords compute to the initial value only when the
        // writing mode is vertical, and we're testing with a horizontal
        // writing mode
        "-moz-max-content", "-moz-min-content", "-moz-fit-content",
        // whether -moz-available computes to the initial value depends on
        // the container size, and for the container size we're testing
        // with, it does
        // "-moz-available",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "none" ],
    },
    "margin-block-end": {
      domProp: "marginBlockEnd",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* XXX testing auto has prerequisites */
      initial_values: [ "0", "0px", "0%", "calc(0pt)", "calc(0% + 0px)" ],
      other_values: [ "1px", "2em", "5%",
        "calc(2px)",
        "calc(-2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "..25px", ".+5px", ".px", "-.px", "++5px", "-+4px", "+-3px", "--7px", "+-.6px", "-+.5px", "++.7px", "--.4px" ],
    },
    "margin-block-start": {
      domProp: "marginBlockStart",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* XXX testing auto has prerequisites */
      initial_values: [ "0", "0px", "0%", "calc(0pt)", "calc(0% + 0px)" ],
      other_values: [ "1px", "2em", "5%",
        "calc(2px)",
        "calc(-2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "..25px", ".+5px", ".px", "-.px", "++5px", "-+4px", "+-3px", "--7px", "+-.6px", "-+.5px", "++.7px", "--.4px" ],
    },
    "-moz-margin-end": {
      domProp: "MozMarginEnd",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "margin-inline-end",
      subproperties: [ "margin-inline-end" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-margin-start": {
      domProp: "MozMarginStart",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "margin-inline-start",
      subproperties: [ "margin-inline-start" ],
      get_computed: logical_box_prop_get_computed,
    },
    "max-block-size": {
      domProp: "maxBlockSize",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      axis: true,
      get_computed: logical_axis_prop_get_computed,
      prerequisites: { "display": "block" },
      initial_values: [ "none" ],
      other_values: [ "30px", "50%",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "auto", "5", "-moz-max-content", "-moz-min-content", "-moz-fit-content", "-moz-available" ]
    },
    "max-inline-size": {
      domProp: "maxInlineSize",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      axis: true,
      get_computed: logical_axis_prop_get_computed,
      prerequisites: { "display": "block" },
      initial_values: [ "none" ],
      other_values: [ "30px", "50%",
        // these four keywords compute to the initial value only when the
        // writing mode is vertical, and we're testing with a horizontal
        // writing mode
        "-moz-max-content", "-moz-min-content", "-moz-fit-content", "-moz-available",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "auto", "5" ]
    },
    "min-block-size": {
      domProp: "minBlockSize",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      axis: true,
      get_computed: logical_axis_prop_get_computed,
      prerequisites: { "display": "block" },
      initial_values: [ "auto", "0", "calc(0em)", "calc(-2px)", "calc(-1%)" ],
      other_values: [ "30px", "50%",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "none", "5", "-moz-max-content", "-moz-min-content", "-moz-fit-content", "-moz-available" ]
    },
    "min-inline-size": {
      domProp: "minInlineSize",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      axis: true,
      get_computed: logical_axis_prop_get_computed,
      prerequisites: { "display": "block" },
      initial_values: [ "auto", "0", "calc(0em)", "calc(-2px)", "calc(-1%)" ],
      other_values: [ "30px", "50%",
        // these four keywords compute to the initial value only when the
        // writing mode is vertical, and we're testing with a horizontal
        // writing mode
        "-moz-max-content", "-moz-min-content", "-moz-fit-content", "-moz-available",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ "none", "5" ]
    },
    "offset-block-end": {
      domProp: "offsetBlockEnd",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* FIXME: run tests with multiple prerequisites */
      prerequisites: { "position": "relative" },
      /* XXX 0 may or may not be equal to auto */
      initial_values: [ "auto" ],
      other_values: [ "32px", "-3em", "12%",
        "calc(2px)",
        "calc(-2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: []
    },
    "offset-block-start": {
      domProp: "offsetBlockStart",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* FIXME: run tests with multiple prerequisites */
      prerequisites: { "position": "relative" },
      /* XXX 0 may or may not be equal to auto */
      initial_values: [ "auto" ],
      other_values: [ "32px", "-3em", "12%",
        "calc(2px)",
        "calc(-2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: []
    },
    "offset-inline-end": {
      domProp: "offsetInlineEnd",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* FIXME: run tests with multiple prerequisites */
      prerequisites: { "position": "relative" },
      /* XXX 0 may or may not be equal to auto */
      initial_values: [ "auto" ],
      other_values: [ "32px", "-3em", "12%",
        "calc(2px)",
        "calc(-2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: []
    },
    "offset-inline-start": {
      domProp: "offsetInlineStart",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      /* FIXME: run tests with multiple prerequisites */
      prerequisites: { "position": "relative" },
      /* XXX 0 may or may not be equal to auto */
      initial_values: [ "auto" ],
      other_values: [ "32px", "-3em", "12%",
        "calc(2px)",
        "calc(-2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: []
    },
    "padding-block-end": {
      domProp: "paddingBlockEnd",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      initial_values: [ "0", "0px", "0%", "calc(0pt)", "calc(0% + 0px)", "calc(-3px)", "calc(-1%)" ],
      other_values: [ "1px", "2em", "5%",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ ],
    },
    "padding-block-start": {
      domProp: "paddingBlockStart",
      inherited: false,
      type: CSS_TYPE_LONGHAND,
      logical: true,
      get_computed: logical_box_prop_get_computed,
      initial_values: [ "0", "0px", "0%", "calc(0pt)", "calc(0% + 0px)", "calc(-3px)", "calc(-1%)" ],
      other_values: [ "1px", "2em", "5%",
        "calc(2px)",
        "calc(50%)",
        "calc(3*25px)",
        "calc(25px*3)",
        "calc(3*25px + 50%)",
      ],
      invalid_values: [ ],
    },
    "-moz-padding-end": {
      domProp: "MozPaddingEnd",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "padding-inline-end",
      subproperties: [ "padding-inline-end" ],
      get_computed: logical_box_prop_get_computed,
    },
    "-moz-padding-start": {
      domProp: "MozPaddingStart",
      inherited: false,
      type: CSS_TYPE_SHORTHAND_AND_LONGHAND,
      alias_for: "padding-inline-start",
      subproperties: [ "padding-inline-start" ],
      get_computed: logical_box_prop_get_computed,
    },
  };
  for (var prop in verticalTextProperties) {
    gCSSProperties[prop] = verticalTextProperties[prop];
  }
  /*
   * Vertical vs horizontal writing-mode can affect line-height
   * because font metrics may not be symmetrical,
   * so we require writing-mode:initial to ensure consistency
   * in font shorthand and line-height tests.
   */
  ["font", "line-height"].forEach(function(prop) {
    var p = gCSSProperties[prop];
    if (p.prerequisites === undefined) {
      p.prerequisites = {};
    }
    p.prerequisites["writing-mode"] = "initial";
  });
}

if (IsCSSPropertyPrefEnabled("layout.css.text-combine-upright.enabled")) {
  gCSSProperties["text-combine-upright"] = {
    domProp: "textCombineUpright",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "all", "digits", "digits 2", "digits 3", "digits 4", "digits     3" ],
    invalid_values: [ "auto", "all 2", "none all", "digits -3", "digits 0",
                      "digits 12", "none 3", "digits 3.1415", "digits3", "digits 1",
                      "digits 3 all", "digits foo", "digits all", "digits 3.0" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.masking.enabled")) {
  gCSSProperties["mask-type"] = {
    domProp: "maskType",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "luminance" ],
    other_values: [ "alpha" ],
    invalid_values: []
  };
}

if (IsCSSPropertyPrefEnabled("svg.paint-order.enabled")) {
  gCSSProperties["paint-order"] = {
    domProp: "paintOrder",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "normal" ],
    other_values: [ "fill", "fill stroke", "fill stroke markers", "stroke markers fill" ],
    invalid_values: [ "fill stroke markers fill", "fill normal" ]
  };
}

if (IsCSSPropertyPrefEnabled("svg.transform-box.enabled")) {
  gCSSProperties["transform-box"] = {
    domProp: "transformBox",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "border-box" ],
    other_values: [ "fill-box", "view-box" ],
    invalid_values: []
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.clip-path-shapes.enabled")) {
  gCSSProperties["clip-path"] = {
    domProp: "clipPath",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [
      // SVG reference clip-path
      "url(#my-clip-path)",

      "polygon(20px 20px)",
      "polygon(20px 20%)",
      "polygon(20% 20%)",
      "polygon(20rem 20em)",
      "polygon(20cm 20mm)",
      "polygon(20px 20px, 30px 30px)",
      "polygon(20px 20px, 30% 30%, 30px 30px)",
      "polygon(nonzero, 20px 20px, 30% 30%, 30px 30px)",
      "polygon(evenodd, 20px 20px, 30% 30%, 30px 30px)",

      "content-box",
      "padding-box",
      "border-box",
      "margin-box",
      "fill-box",
      "stroke-box",
      "view-box",

      "polygon(0 0) content-box",
      "border-box polygon(0 0)",
      "padding-box    polygon(   0  20px ,  30px    20% )  ",
      "polygon(evenodd, 20% 20em) content-box",
      "polygon(evenodd, 20vh 20em) padding-box",
      "polygon(evenodd, 20vh calc(20% + 20em)) border-box",
      "polygon(evenodd, 20vh 20vw) margin-box",
      "polygon(evenodd, 20pt 20cm) fill-box",
      "polygon(evenodd, 20ex 20pc) stroke-box",
      "polygon(evenodd, 20rem 20in) view-box",

      "circle()",
      "circle(at center)",
      "circle(at top left 20px)",
      "circle(at bottom right)",
      "circle(20%)",
      "circle(300px)",
      "circle(calc(20px + 30px))",
      "circle(farthest-side)",
      "circle(closest-side)",
      "circle(closest-side at center)",
      "circle(farthest-side at top)",
      "circle(20px at top right)",
      "circle(40% at 50% 100%)",
      "circle(calc(20% + 20%) at right bottom)",
      "circle() padding-box",

      "ellipse()",
      "ellipse(at center)",
      "ellipse(at top left 20px)",
      "ellipse(at bottom right)",
      "ellipse(20% 20%)",
      "ellipse(300px 50%)",
      "ellipse(calc(20px + 30px) 10%)",
      "ellipse(farthest-side closest-side)",
      "ellipse(closest-side farthest-side)",
      "ellipse(farthest-side farthest-side)",
      "ellipse(closest-side closest-side)",
      "ellipse(closest-side closest-side at center)",
      "ellipse(20% farthest-side at top)",
      "ellipse(20px 50% at top right)",
      "ellipse(closest-side 40% at 50% 100%)",
      "ellipse(calc(20% + 20%) calc(20px + 20cm) at right bottom)",

      "inset(1px)",
      "inset(20% -20px)",
      "inset(20em 4rem calc(20% + 20px))",
      "inset(20vh 20vw 20pt 3%)",
      "inset(5px round 3px)",
      "inset(1px 2px round 3px / 3px)",
      "inset(1px 2px 3px round 3px 2em / 20%)",
      "inset(1px 2px 3px 4px round 3px 2vw 20% / 20px 3em 2vh 20%)",
    ],
    invalid_values: [
      "url(#test) url(#tes2)",
      "polygon (0 0)",
      "polygon(20px, 40px)",
      "border-box content-box",
      "polygon(0 0) polygon(0 0)",
      "polygon(nonzero 0 0)",
      "polygon(evenodd 20px 20px)",
      "polygon(20px 20px, evenodd)",
      "polygon(20px 20px, nonzero)",
      "polygon(0 0) conten-box content-box",
      "content-box polygon(0 0) conten-box",
      "padding-box polygon(0 0) conten-box",
      "polygon(0 0) polygon(0 0) content-box",
      "polygon(0 0) content-box polygon(0 0)",
      "polygon(0 0), content-box",
      "polygon(0 0), polygon(0 0)",
      "content-box polygon(0 0) polygon(0 0)",
      "content-box polygon(0 0) none",
      "none content-box polygon(0 0)",
      "inherit content-box polygon(0 0)",
      "initial polygon(0 0)",
      "polygon(0 0) farthest-side",
      "farthest-corner polygon(0 0)",
      "polygon(0 0) farthest-corner",
      "polygon(0 0) conten-box",
      "polygon(0 0) polygon(0 0) farthest-corner",
      "polygon(0 0) polygon(0 0) polygon(0 0)",
      "border-box polygon(0, 0)",
      "border-box padding-box",
      "margin-box farthest-side",
      "nonsense() border-box",
      "border-box nonsense()",

      "circle(at)",
      "circle(at 20% 20% 30%)",
      "circle(20px 2px at center)",
      "circle(2at center)",
      "circle(closest-corner)",
      "circle(at center top closest-side)",
      "circle(-20px)",
      "circle(farthest-side closest-side)",
      "circle(20% 20%)",
      "circle(at farthest-side)",
      "circle(calc(20px + rubbish))",

      "ellipse(at)",
      "ellipse(at 20% 20% 30%)",
      "ellipse(20px at center)",
      "ellipse(-20px 20px)",
      "ellipse(closest-corner farthest-corner)",
      "ellipse(20px -20px)",
      "ellipse(-20px -20px)",
      "ellipse(farthest-side)",
      "ellipse(20%)",
      "ellipse(at farthest-side farthest-side)",
      "ellipse(at top left calc(20px + rubbish))",

      "polygon(at)",
      "polygon(at 20% 20% 30%)",
      "polygon(20px at center)",
      "polygon(2px 2at center)",
      "polygon(closest-corner farthest-corner)",
      "polygon(at center top closest-side closest-side)",
      "polygon(40% at 50% 100%)",
      "polygon(40% farthest-side 20px at 50% 100%)",

      "inset()",
      "inset(round)",
      "inset(round 3px)",
      "inset(1px round 1px 2px 3px 4px 5px)",
      "inset(1px 2px 3px 4px 5px)",
      "inset(1px, round 3px)",
      "inset(1px, 2px)",
      "inset(1px 2px, 3px)",
      "inset(1px at 3px)",
      "inset(1px round 1px // 2px)",
      "inset(1px round)",
      "inset(1px calc(2px + rubbish))",
      "inset(1px round 2px calc(3px + rubbish))",
    ],
    unbalanced_values: [
      "polygon(30% 30%",
      "polygon(nonzero, 20% 20px",
      "polygon(evenodd, 20px 20px",

      "circle(",
      "circle(40% at 50% 100%",
      "ellipse(",
      "ellipse(40% at 50% 100%",

      "inset(1px",
      "inset(1px 2px",
      "inset(1px 2px 3px",
      "inset(1px 2px 3px 4px",
      "inset(1px 2px 3px 4px round 5px",
      "inset(1px 2px 3px 4px round 5px / 6px",
    ]
  };
}


if (IsCSSPropertyPrefEnabled("layout.css.filters.enabled")) {
  gCSSProperties["filter"] = {
    domProp: "filter",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [
      // SVG reference filters
      "url(#my-filter)",
      "url(#my-filter-1) url(#my-filter-2)",

      // Filter functions
      "opacity(50%) saturate(1.0)",
      "invert(50%) sepia(0.1) brightness(90%)",

      // Mixed SVG reference filters and filter functions
      "grayscale(1) url(#my-filter-1)",
      "url(#my-filter-1) brightness(50%) contrast(0.9)",

      // Bad URLs
      "url('badscheme:badurl')",
      "blur(3px) url('badscheme:badurl') grayscale(50%)",

      "blur(0)",
      "blur(0px)",
      "blur(0.5px)",
      "blur(3px)",
      "blur(100px)",
      "blur(0.1em)",
      "blur(calc(-1px))", // Parses and becomes blur(0px).
      "blur(calc(0px))",
      "blur(calc(5px))",
      "blur(calc(2 * 5px))",

      "brightness(0)",
      "brightness(50%)",
      "brightness(1)",
      "brightness(1.0)",
      "brightness(2)",
      "brightness(350%)",
      "brightness(4.567)",

      "contrast(0)",
      "contrast(50%)",
      "contrast(1)",
      "contrast(1.0)",
      "contrast(2)",
      "contrast(350%)",
      "contrast(4.567)",

      "drop-shadow(2px 2px)",
      "drop-shadow(2px 2px 1px)",
      "drop-shadow(2px 2px green)",
      "drop-shadow(2px 2px 1px green)",
      "drop-shadow(green 2px 2px)",
      "drop-shadow(green 2px 2px 1px)",
      "drop-shadow(currentColor 3px 3px)",
      "drop-shadow(2px 2px calc(-5px))", /* clamped */
      "drop-shadow(calc(3em - 2px) 2px green)",
      "drop-shadow(green calc(3em - 2px) 2px)",
      "drop-shadow(2px calc(2px + 0.2em))",
      "drop-shadow(blue 2px calc(2px + 0.2em))",
      "drop-shadow(2px calc(2px + 0.2em) blue)",
      "drop-shadow(calc(-2px) calc(-2px))",
      "drop-shadow(-2px -2px)",
      "drop-shadow(calc(2px) calc(2px))",
      "drop-shadow(calc(2px) calc(2px) calc(2px))",

      "grayscale(0)",
      "grayscale(50%)",
      "grayscale(1)",
      "grayscale(1.0)",
      "grayscale(2)",
      "grayscale(350%)",
      "grayscale(4.567)",

      "hue-rotate(0deg)",
      "hue-rotate(90deg)",
      "hue-rotate(540deg)",
      "hue-rotate(-90deg)",
      "hue-rotate(10grad)",
      "hue-rotate(1.6rad)",
      "hue-rotate(-1.6rad)",
      "hue-rotate(0.5turn)",
      "hue-rotate(-2turn)",

      "invert(0)",
      "invert(50%)",
      "invert(1)",
      "invert(1.0)",
      "invert(2)",
      "invert(350%)",
      "invert(4.567)",

      "opacity(0)",
      "opacity(50%)",
      "opacity(1)",
      "opacity(1.0)",
      "opacity(2)",
      "opacity(350%)",
      "opacity(4.567)",

      "saturate(0)",
      "saturate(50%)",
      "saturate(1)",
      "saturate(1.0)",
      "saturate(2)",
      "saturate(350%)",
      "saturate(4.567)",

      "sepia(0)",
      "sepia(50%)",
      "sepia(1)",
      "sepia(1.0)",
      "sepia(2)",
      "sepia(350%)",
      "sepia(4.567)",
    ],
    invalid_values: [
      // none
      "none none",
      "url(#my-filter) none",
      "none url(#my-filter)",
      "blur(2px) none url(#my-filter)",

      // Nested filters
      "grayscale(invert(1.0))",

      // Comma delimited filters
      "url(#my-filter),",
      "invert(50%), url(#my-filter), brightness(90%)",

      // Test the following situations for each filter function:
      // - Invalid number of arguments
      // - Comma delimited arguments
      // - Wrong argument type
      // - Argument value out of range
      "blur()",
      "blur(3px 5px)",
      "blur(3px,)",
      "blur(3px, 5px)",
      "blur(#my-filter)",
      "blur(0.5)",
      "blur(50%)",
      "blur(calc(0))", // Unitless zero in calc is not a valid length.
      "blur(calc(0.1))",
      "blur(calc(10%))",
      "blur(calc(20px - 5%))",
      "blur(-3px)",

      "brightness()",
      "brightness(0.5 0.5)",
      "brightness(0.5,)",
      "brightness(0.5, 0.5)",
      "brightness(#my-filter)",
      "brightness(10px)",
      "brightness(-1)",

      "contrast()",
      "contrast(0.5 0.5)",
      "contrast(0.5,)",
      "contrast(0.5, 0.5)",
      "contrast(#my-filter)",
      "contrast(10px)",
      "contrast(-1)",

      "drop-shadow()",
      "drop-shadow(3% 3%)",
      "drop-shadow(2px 2px -5px)",
      "drop-shadow(2px 2px 2px 2px)",
      "drop-shadow(2px 2px, none)",
      "drop-shadow(none, 2px 2px)",
      "drop-shadow(inherit, 2px 2px)",
      "drop-shadow(2px 2px, inherit)",
      "drop-shadow(2 2px)",
      "drop-shadow(2px 2)",
      "drop-shadow(2px 2px 2)",
      "drop-shadow(2px 2px 2px 2)",
      "drop-shadow(calc(2px) calc(2px) calc(2px) calc(2px))",
      "drop-shadow(green 2px 2px, blue 1px 3px 4px)",
      "drop-shadow(blue 2px 2px, currentColor 1px 2px)",

      "grayscale()",
      "grayscale(0.5 0.5)",
      "grayscale(0.5,)",
      "grayscale(0.5, 0.5)",
      "grayscale(#my-filter)",
      "grayscale(10px)",
      "grayscale(-1)",

      "hue-rotate()",
      "hue-rotate(0)",
      "hue-rotate(0.5 0.5)",
      "hue-rotate(0.5,)",
      "hue-rotate(0.5, 0.5)",
      "hue-rotate(#my-filter)",
      "hue-rotate(10px)",
      "hue-rotate(-1)",
      "hue-rotate(45deg,)",

      "invert()",
      "invert(0.5 0.5)",
      "invert(0.5,)",
      "invert(0.5, 0.5)",
      "invert(#my-filter)",
      "invert(10px)",
      "invert(-1)",

      "opacity()",
      "opacity(0.5 0.5)",
      "opacity(0.5,)",
      "opacity(0.5, 0.5)",
      "opacity(#my-filter)",
      "opacity(10px)",
      "opacity(-1)",

      "saturate()",
      "saturate(0.5 0.5)",
      "saturate(0.5,)",
      "saturate(0.5, 0.5)",
      "saturate(#my-filter)",
      "saturate(10px)",
      "saturate(-1)",

      "sepia()",
      "sepia(0.5 0.5)",
      "sepia(0.5,)",
      "sepia(0.5, 0.5)",
      "sepia(#my-filter)",
      "sepia(10px)",
      "sepia(-1)",
    ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.grid.enabled")) {
  var isGridTemplateSubgridValueEnabled =
    IsCSSPropertyPrefEnabled("layout.css.grid-template-subgrid-value.enabled");

  gCSSProperties["display"].other_values.push("grid", "inline-grid");
  gCSSProperties["grid-auto-flow"] = {
    domProp: "gridAutoFlow",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "row" ],
    other_values: [
      "column",
      "column dense",
      "row dense",
      "dense column",
      "dense row",
      "dense",
    ],
    invalid_values: [
      "",
      "auto",
      "none",
      "10px",
      "column row",
      "dense row dense",
    ]
  };

  gCSSProperties["grid-auto-columns"] = {
    domProp: "gridAutoColumns",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: [
      "40px",
      "2em",
      "2.5fr",
      "12%",
      "min-content",
      "max-content",
      "calc(20px + 10%)",
      "minmax(20px, max-content)",
      "minmax(min-content, auto)",
      "minmax(auto, max-content)",
      "m\\69nmax(20px, 4Fr)",
      "MinMax(min-content, calc(20px + 10%))",
    ],
    invalid_values: [
      "",
      "normal",
      "40ms",
      "-40px",
      "-12%",
      "-2em",
      "-2.5fr",
      "minmax()",
      "minmax(20px)",
      "mİnmax(20px, 100px)",
      "minmax(20px, 100px, 200px)",
      "maxmin(100px, 20px)",
      "minmax(min-content, minmax(30px, max-content))",
    ]
  };
  gCSSProperties["grid-auto-rows"] = {
    domProp: "gridAutoRows",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: gCSSProperties["grid-auto-columns"].initial_values,
    other_values: gCSSProperties["grid-auto-columns"].other_values,
    invalid_values: gCSSProperties["grid-auto-columns"].invalid_values
  };

  gCSSProperties["grid-template-columns"] = {
    domProp: "gridTemplateColumns",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [
      "auto",
      "40px",
      "2.5fr",
      "[normal] 40px [] auto [ ] 12%",
      "[foo] 40px min-content [ bar ] calc(20px + 10%) max-content",
      "40px min-content calc(20px + 10%) max-content",
      "minmax(min-content, auto)",
      "minmax(auto, max-content)",
      "m\\69nmax(20px, 4Fr)",
      "40px MinMax(min-content, calc(20px + 10%)) max-content",
      "40px 2em",
      "[] 40px [-foo] 2em [bar baz This\ is\ one\ ident]",
      // TODO bug 978478: "[a] repeat(3, [b] 20px [c] 40px [d]) [e]",
      "repeat(1, 20px)",
      "repeat(1, [a] 20px)",
      "[a] Repeat(4, [a] 20px [] auto [b c]) [d]",
      "[a] 2.5fr Repeat(4, [a] 20px [] auto [b c]) [d]",
      "[a] 2.5fr [z] Repeat(4, [a] 20px [] auto [b c]) [d]",
      "[a] 2.5fr [z] Repeat(4, [a] 20px [] auto) [d]",
      "[a] 2.5fr [z] Repeat(4, 20px [b c] auto [b c]) [d]",
      "[a] 2.5fr [z] Repeat(4, 20px auto) [d]",
      "repeat(auto-fill, 0)",
      "[a] repeat( Auto-fill,1%)",
      "[a] repeat(Auto-fit, 0)",
      "repeat(Auto-fit,[] 1%)",
      "repeat(auto-fit, [a] 1em) auto",
      "[a] repeat( auto-fit,[a b] minmax(0,0) )",
      "[a] 40px repeat(auto-fit,[a b] minmax(1px, 0) [])",
      "[a] auto [b] repeat(auto-fit,[a b] minmax(1mm, 1%) [c]) [c] auto",
    ],
    invalid_values: [
      "",
      "normal",
      "40ms",
      "-40px",
      "-12%",
      "-2fr",
      "(foo)",
      "(inherit) 40px",
      "(initial) 40px",
      "(unset) 40px",
      "(default) 40px",
      "(6%) 40px",
      "(5th) 40px",
      "(foo() bar) 40px",
      "(foo)) 40px",
      "(foo) 40px",
      "(foo) (bar) 40px",
      "40px (foo) (bar)",
      "minmax()",
      "minmax(20px)",
      "mİnmax(20px, 100px)",
      "minmax(20px, 100px, 200px)",
      "maxmin(100px, 20px)",
      "minmax(min-content, minmax(30px, max-content))",
      "repeat(0, 20px)",
      "repeat(-3, 20px)",
      "rêpeat(1, 20px)",
      "repeat(1)",
      "repeat(1, )",
      "repeat(3px, 20px)",
      "repeat(2.0, 20px)",
      "repeat(2.5, 20px)",
      "repeat(2, (foo))",
      "repeat(2, foo)",
      "40px calc(0px + rubbish)",
      "repeat(1, repeat(1, 20px))",
      "repeat(auto-fill, auto)",
      "repeat(auto-fit,auto)",
      "repeat(auto-fit,[])",
      "repeat(auto-fill, 0) repeat(auto-fit, 0) ",
      "repeat(auto-fit, 0) repeat(auto-fill, 0) ",
      "[a] repeat(auto-fit, 0) repeat(auto-fit, 0) ",
      "[a] repeat(auto-fill, 0) [a] repeat(auto-fill, 0) ",
      "repeat(auto-fill, 0 0)",
      "repeat(auto-fill, 0 [] 0)",
      "repeat(auto-fill, min-content)",
      "repeat(auto-fit,max-content)",
      "repeat(auto-fit,minmax(auto,auto))",
      "repeat(auto-fit,[] minmax(1px, min-content))",
      "repeat(auto-fit,[a] minmax(1%, auto) [])",
    ],
    unbalanced_values: [
      "(foo] 40px",
    ]
  };
  if (isGridTemplateSubgridValueEnabled) {
    gCSSProperties["grid-template-columns"].other_values.push(
      // See https://bugzilla.mozilla.org/show_bug.cgi?id=981300
      "[none auto subgrid min-content max-content foo] 40px",

      "subgrid",
      "subgrid [] [foo bar]",
      "subgrid repeat(1, [])",
      "subgrid Repeat(4, [a] [b c] [] [d])",
      "subgrid repeat(auto-fill, [])",
      "subgrid [x] repeat( Auto-fill, [a b c]) []",
      "subgrid [x] repeat(auto-fill, []) [y z]"
    );
    gCSSProperties["grid-template-columns"].invalid_values.push(
      "subgrid (foo) 40px",
      "subgrid (foo 40px)",
      "(foo) subgrid",
      "subgrid rêpeat(1, ())",
      "subgrid repeat(0, ())",
      "subgrid repeat(-3, ())",
      "subgrid repeat(2.0, ())",
      "subgrid repeat(2.5, ())",
      "subgrid repeat(3px, ())",
      "subgrid repeat(1)",
      "subgrid repeat(1, )",
      "subgrid repeat(2, (40px))",
      "subgrid repeat(2, foo)",
      "subgrid repeat(1, repeat(1, []))",
      "subgrid repeat(auto-fit,[])",
      "subgrid [] repeat(auto-fit,[])",
      "subgrid [a] repeat(auto-fit,[])",
      "subgrid repeat(auto-fill, 1px)",
      "subgrid repeat(auto-fill, 1px [])",
      "subgrid repeat(Auto-fill, [a] [b c] [] [d])",
      "subgrid repeat(auto-fill, []) repeat(auto-fill, [])"
    );
  }
  gCSSProperties["grid-template-rows"] = {
    domProp: "gridTemplateRows",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: gCSSProperties["grid-template-columns"].initial_values,
    other_values: gCSSProperties["grid-template-columns"].other_values,
    invalid_values: gCSSProperties["grid-template-columns"].invalid_values
  };
  gCSSProperties["grid-template-areas"] = {
    domProp: "gridTemplateAreas",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [
      "''",
      "'' ''",
      "'1a-é_ .' \"b .\"",
      "' Z\t\\aZ' 'Z Z'",
      " '. . a b'  '. .a b' ",
      "'a.b' '. . .'",
      "'.' '..'",
      "'...' '.'",
      "'...-blah' '. .'",
      "'.. ..' '.. ...'",
    ],
    invalid_values: [
      "'a b' 'a/b'",
      "'a . a'",
      "'. a a' 'a a a'",
      "'a a .' 'a a a'",
      "'a a' 'a .'",
      "'a a'\n'..'\n'a a'",
    ]
  };

  gCSSProperties["grid-template"] = {
    domProp: "gridTemplate",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "grid-template-areas",
      "grid-template-rows",
      "grid-template-columns",
    ],
    initial_values: [
      "none",
      "none / none",
    ],
    other_values: [
      // <'grid-template-rows'> / <'grid-template-columns'>
      "40px / 100px",
      "[foo] 40px [bar] / [baz] 100px [fizz]",
      " none/100px",
      "40px/none",
      // [ <track-list> / ]? [ <line-names>? <string> <track-size>? <line-names>? ]+
      "'fizz'",
      "[bar] 'fizz'",
      "'fizz' / [foo] 40px",
      "[bar] 'fizz' / [foo] 40px",
      "'fizz' 100px / [foo] 40px",
      "[bar] 'fizz' 100px / [foo] 40px",
      "[bar] 'fizz' 100px [buzz] / [foo] 40px",
      "[bar] 'fizz' 100px [buzz] \n [a] '.' 200px [b] / [foo] 40px",
    ],
    invalid_values: [
      "[foo] [bar] 40px / 100px",
      "[fizz] [buzz] 100px / 40px",
      "[fizz] [buzz] 'foo' / 40px",
      "'foo' / none"
    ]
  };
  if (isGridTemplateSubgridValueEnabled) {
    gCSSProperties["grid-template"].other_values.push(
      "subgrid",
      "subgrid/40px 20px",
      "subgrid [foo] [] [bar baz] / 40px 20px",
      "40px 20px/subgrid",
      "40px 20px/subgrid  [foo] [] repeat(3, [a] [b]) [bar baz]",
      "subgrid/subgrid",
      "subgrid [foo] [] [bar baz]/subgrid [foo] [] [bar baz]"
    );
    gCSSProperties["grid-template"].invalid_values.push(
      "subgrid []",
      "subgrid [] / 'fizz'",
      "subgrid / 'fizz'"
    );
  }

  gCSSProperties["grid"] = {
    domProp: "grid",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "grid-template-areas",
      "grid-template-rows",
      "grid-template-columns",
      "grid-auto-flow",
      "grid-auto-rows",
      "grid-auto-columns",
      "grid-column-gap",
      "grid-row-gap",
    ],
    initial_values: [
      "none",
      "none / none",
    ],
    other_values: [
      "column 40px",
      "column dense auto",
      "dense row minmax(min-content, 2fr)",
      "row 40px / 100px",
    ].concat(
      gCSSProperties["grid-template"].other_values,
      gCSSProperties["grid-auto-flow"].other_values
    ),
    invalid_values: [
      "row column 40px",
      "row -20px",
      "row 200ms",
      "row 40px 100px",
    ].concat(
      gCSSProperties["grid-template"].invalid_values,
      gCSSProperties["grid-auto-flow"].invalid_values
        .filter((v) => v != 'none')
    )
  };

  var gridLineOtherValues = [
    "foo",
    "2",
    "2 foo",
    "foo 2",
    "-3",
    "-3 bar",
    "bar -3",
    "span 2",
    "2 span",
    "span foo",
    "foo span",
    "span 2 foo",
    "span foo 2",
    "2 foo span",
    "foo 2 span",
  ];
  var gridLineInvalidValues = [
    "",
    "4th",
    "span",
    "inherit 2",
    "2 inherit",
    "20px",
    "2 3",
    "2.5",
    "2.0",
    "0",
    "0 foo",
    "span 0",
    "2 foo 3",
    "foo 2 foo",
    "2 span foo",
    "foo span 2",
    "span -3",
    "span -3 bar",
    "span 2 span",
    "span foo span",
    "span 2 foo span",
  ];

  gCSSProperties["grid-column-start"] = {
    domProp: "gridColumnStart",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: gridLineOtherValues,
    invalid_values: gridLineInvalidValues
  };
  gCSSProperties["grid-column-end"] = {
    domProp: "gridColumnEnd",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: gridLineOtherValues,
    invalid_values: gridLineInvalidValues
  };
  gCSSProperties["grid-row-start"] = {
    domProp: "gridRowStart",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: gridLineOtherValues,
    invalid_values: gridLineInvalidValues
  };
  gCSSProperties["grid-row-end"] = {
    domProp: "gridRowEnd",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: gridLineOtherValues,
    invalid_values: gridLineInvalidValues
  };

  // The grid-column and grid-row shorthands take values of the form
  //   <grid-line> [ / <grid-line> ]?
  var gridColumnRowOtherValues = [].concat(gridLineOtherValues);
  gridLineOtherValues.concat([ "auto" ]).forEach(function(val) {
    gridColumnRowOtherValues.push(" foo / " + val);
    gridColumnRowOtherValues.push(val + "/2");
  });
  var gridColumnRowInvalidValues = [
    "foo, bar",
    "foo / bar / baz",
  ].concat(gridLineInvalidValues);
  gridLineInvalidValues.forEach(function(val) {
    gridColumnRowInvalidValues.push("span 3 / " + val);
    gridColumnRowInvalidValues.push(val + " / foo");
  });
  gCSSProperties["grid-column"] = {
    domProp: "gridColumn",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "grid-column-start",
      "grid-column-end"
    ],
    initial_values: [ "auto", "auto / auto" ],
    other_values: gridColumnRowOtherValues,
    invalid_values: gridColumnRowInvalidValues
  };
  gCSSProperties["grid-row"] = {
    domProp: "gridRow",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "grid-row-start",
      "grid-row-end"
    ],
    initial_values: [ "auto", "auto / auto" ],
    other_values: gridColumnRowOtherValues,
    invalid_values: gridColumnRowInvalidValues
  };

  var gridAreaOtherValues = gridLineOtherValues.slice();
  gridLineOtherValues.forEach(function(val) {
    gridAreaOtherValues.push("foo / " + val);
    gridAreaOtherValues.push(val + "/2/3");
    gridAreaOtherValues.push("foo / bar / " + val + " / baz");
  });
  var gridAreaInvalidValues = [
    "foo, bar",
    "foo / bar / baz / fizz / buzz",
    "default / foo / bar / baz",
    "foo / initial / bar / baz",
    "foo / bar / inherit / baz",
    "foo / bar / baz / unset",
  ].concat(gridLineInvalidValues);
  gridLineInvalidValues.forEach(function(val) {
    gridAreaInvalidValues.push("foo / " + val);
    gridAreaInvalidValues.push("foo / bar / " + val);
    gridAreaInvalidValues.push("foo / 4 / bar / " + val);
  });

  gCSSProperties["grid-area"] = {
    domProp: "gridArea",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [
      "grid-row-start",
      "grid-column-start",
      "grid-row-end",
      "grid-column-end"
    ],
    initial_values: [
      "auto",
      "auto / auto",
      "auto / auto / auto",
      "auto / auto / auto / auto"
    ],
    other_values: gridAreaOtherValues,
    invalid_values: gridAreaInvalidValues
  };

  gCSSProperties["grid-column-gap"] = {
    domProp: "gridColumnGap",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "0" ],
    other_values: [ "2px", "1em", "calc(1px + 1em)" ],
    invalid_values: [ "-1px", "2%", "auto", "none", "1px 1px", "calc(1%)" ],
  };
  gCSSProperties["grid-row-gap"] = {
    domProp: "gridRowGap",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "0" ],
    other_values: [ "2px", "1em", "calc(1px + 1em)" ],
    invalid_values: [ "-1px", "2%", "auto", "none", "1px 1px", "calc(1%)" ],
  };
  gCSSProperties["grid-gap"] = {
    domProp: "gridGap",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [ "grid-column-gap", "grid-row-gap" ],
    initial_values: [ "0", "0 0" ],
    other_values: [ "1ch 0", "1em 1px", "calc(1px + 1ch)" ],
    invalid_values: [ "-1px", "1px -1px", "1px 1px 1px", "inherit 1px",
                      "1px 1%", "1px auto" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.display-contents.enabled")) {
  gCSSProperties["display"].other_values.push("contents");
}

if (IsCSSPropertyPrefEnabled("layout.css.contain.enabled")) {
  gCSSProperties["contain"] = {
    domProp: "contain",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [
      "strict",
      "layout",
      "style",
      "layout style",
      "style layout",
      "paint",
      "layout paint",
      "paint layout",
      "style paint",
      "paint style",
      "layout style paint",
      "layout paint style",
      "style paint layout",
      "paint style layout",
    ],
    invalid_values: [
      "none strict",
      "strict layout",
      "strict layout style",
      "layout strict",
      "layout style strict",
      "layout style paint strict",
      "paint strict",
      "style strict",
      "paint paint",
      "strict strict",
      "auto",
      "10px",
      "0",
    ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.image-orientation.enabled")) {
  gCSSProperties["image-orientation"] = {
    domProp: "imageOrientation",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [
      "0deg",
      "0grad",
      "0rad",
      "0turn",

      // Rounded initial values.
      "-90deg",
      "15deg",
      "360deg",
    ],
    other_values: [
      "0deg flip",
      "90deg",
      "90deg flip",
      "180deg",
      "180deg flip",
      "270deg",
      "270deg flip",
      "flip",
      "from-image",

      // Grad units.
      "0grad flip",
      "100grad",
      "100grad flip",
      "200grad",
      "200grad flip",
      "300grad",
      "300grad flip",

      // Radian units.
      "0rad flip",
      "1.57079633rad",
      "1.57079633rad flip",
      "3.14159265rad",
      "3.14159265rad flip",
      "4.71238898rad",
      "4.71238898rad flip",

      // Turn units.
      "0turn flip",
      "0.25turn",
      "0.25turn flip",
      "0.5turn",
      "0.5turn flip",
      "0.75turn",
      "0.75turn flip",

      // Rounded values.
      "-45deg flip",
      "65deg flip",
      "400deg flip",
    ],
    invalid_values: [
      "none",
      "0deg none",
      "flip 0deg",
      "flip 0deg",
      "0",
      "0 flip",
      "flip 0",
      "0deg from-image",
      "from-image 0deg",
      "flip from-image",
      "from-image flip",
    ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.osx-font-smoothing.enabled")) {
  gCSSProperties["-moz-osx-font-smoothing"] = {
    domProp: "MozOsxFontSmoothing",
    inherited: true,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: [ "grayscale" ],
    invalid_values: [ "none", "subpixel-antialiased", "antialiased" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.sticky.enabled")) {
  gCSSProperties["position"].other_values.push("sticky");
}

if (IsCSSPropertyPrefEnabled("layout.css.mix-blend-mode.enabled")) {
  gCSSProperties["mix-blend-mode"] = {
    domProp: "mixBlendMode",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "normal" ],
    other_values: ["multiply", "screen", "overlay", "darken", "lighten", "color-dodge", "color-burn",
        "hard-light", "soft-light", "difference", "exclusion", "hue", "saturation", "color", "luminosity"],
    invalid_values: []
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.isolation.enabled")) {
  gCSSProperties["isolation"] = {
    domProp: "isolation",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: ["isolate"],
    invalid_values: []
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.background-blend-mode.enabled")) {
  gCSSProperties["background-blend-mode"] = {
    domProp: "backgroundBlendMode",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "normal" ],
    other_values: [ "multiply", "screen", "overlay", "darken", "lighten", "color-dodge", "color-burn",
      "hard-light", "soft-light", "difference", "exclusion", "hue", "saturation", "color", "luminosity" ],
    invalid_values: ["none", "10px", "multiply multiply"]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.object-fit-and-position.enabled")) {
  gCSSProperties["object-fit"] = {
    domProp: "objectFit",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "fill" ],
    other_values: [ "contain", "cover", "none", "scale-down" ],
    invalid_values: [ "auto", "5px", "100%" ]
  };
  gCSSProperties["object-position"] = {
    domProp: "objectPosition",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "50% 50%", "50%", "center", "center center" ],
    other_values: [
      "calc(20px)",
      "calc(20px) 10px",
      "10px calc(20px)",
      "calc(20px) 25%",
      "25% calc(20px)",
      "calc(20px) calc(20px)",
      "calc(20px + 1em) calc(20px / 2)",
      "calc(20px + 50%) calc(50% - 10px)",
      "calc(-20px) calc(-50%)",
      "calc(-20%) calc(-50%)",
      "0px 0px",
      "right 20px top 60px",
      "right 20px bottom 60px",
      "left 20px top 60px",
      "left 20px bottom 60px",
      "right -50px top -50px",
      "left -50px bottom -50px",
      "right 20px top -50px",
      "right -20px top 50px",
      "right 3em bottom 10px",
      "bottom 3em right 10px",
      "top 3em right 10px",
      "left 15px",
      "10px top",
      "left top 15px",
      "left 10px top",
      "left 20%",
      "right 20%"
    ],
    invalid_values: [ "center 10px center 4px", "center 10px center",
                      "top 20%", "bottom 20%", "50% left", "top 50%",
                      "50% bottom 10%", "right 10% 50%", "left right",
                      "top bottom", "left 10% right",
                      "top 20px bottom 20px", "left left", "20 20" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.overflow-clip-box.enabled")) {
  gCSSProperties["overflow-clip-box"] = {
    domProp: "overflowClipBox",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "padding-box" ],
    other_values: [ "content-box" ],
    invalid_values: [ "none", "auto", "border-box", "0" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.box-decoration-break.enabled")) {
  gCSSProperties["box-decoration-break"] = {
    domProp: "boxDecorationBreak",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "slice" ],
    other_values: [ "clone" ],
    invalid_values: [ "auto",  "none",  "1px" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.scroll-behavior.property-enabled")) {
  gCSSProperties["scroll-behavior"] = {
    domProp: "scrollBehavior",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "auto" ],
    other_values: [ "smooth" ],
    invalid_values: [ "none",  "1px" ]
  };
}

if (IsCSSPropertyPrefEnabled("layout.css.scroll-snap.enabled")) {
  gCSSProperties["scroll-snap-coordinate"] = {
    domProp: "scrollSnapCoordinate",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "25% 25%", "top", "0px 100px, 10em 50%",
                    "top left, top right, bottom left, bottom right, center",
                    "calc(2px)",
                    "calc(50%)",
                    "calc(3*25px)",
                    "calc(3*25px) 5px",
                    "5px calc(3*25px)",
                    "calc(20%) calc(3*25px)",
                    "calc(25px*3)",
                    "calc(3*25px + 50%)",
                    "calc(20%) calc(3*25px), center"],
    invalid_values: [ "auto", "default" ]
  }
  gCSSProperties["scroll-snap-destination"] = {
    domProp: "scrollSnapDestination",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "0px 0px" ],
    other_values: [ "25% 25%", "6px 5px", "20% 3em", "0in 1in",
                    "top", "right", "top left", "top right", "center",
                    "calc(2px)",
                    "calc(50%)",
                    "calc(3*25px)",
                    "calc(3*25px) 5px",
                    "5px calc(3*25px)",
                    "calc(20%) calc(3*25px)",
                    "calc(25px*3)",
                    "calc(3*25px + 50%)"],
    invalid_values: [ "auto", "none", "default" ]
  }
  gCSSProperties["scroll-snap-points-x"] = {
    domProp: "scrollSnapPointsX",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "repeat(100%)", "repeat(120px)", "repeat(calc(3*25px))" ],
    invalid_values: [ "auto", "1px", "left", "rgb(1,2,3)" ]
  }
  gCSSProperties["scroll-snap-points-y"] = {
    domProp: "scrollSnapPointsY",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: [ "repeat(100%)", "repeat(120px)", "repeat(calc(3*25px))" ],
    invalid_values: [ "auto", "1px", "top", "rgb(1,2,3)" ]
  }
  gCSSProperties["scroll-snap-type"] = {
    domProp: "scrollSnapType",
    inherited: false,
    type: CSS_TYPE_TRUE_SHORTHAND,
    subproperties: [ "scroll-snap-type-x", "scroll-snap-type-y" ],
    initial_values: [ "none" ],
    other_values: [ "mandatory", "proximity" ],
    invalid_values: [ "auto",  "1px" ]
  };
  gCSSProperties["scroll-snap-type-x"] = {
    domProp: "scrollSnapTypeX",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: ["mandatory", "proximity"],
    invalid_values: [ "auto",  "1px" ]
  };
  gCSSProperties["scroll-snap-type-y"] = {
    domProp: "scrollSnapTypeY",
    inherited: false,
    type: CSS_TYPE_LONGHAND,
    initial_values: [ "none" ],
    other_values: ["mandatory", "proximity"],
    invalid_values: [ "auto",  "1px" ]
  };
}

}
