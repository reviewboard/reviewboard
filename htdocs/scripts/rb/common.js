RB = {utils: {}}


// Constants
var STAR_ON_IMG = "/images/star_on.png";
var STAR_OFF_IMG = "/images/star_off.png";

// State variables
var gStars = {};


RB.utils.String = function() {};
RB.utils.String.prototype = {
    strip: function() {
        return this.replace(/^\s+/, '').replace(/\s+$/, '');
    },

    stripTags: function() {
        return this.replace(/<\/?[^>]+>/gi, '');
    },

    htmlEncode: function() {
        if (this == "") {
          return "";
        }

        str = this.replace(/&/g, "&amp;");
        str = str.replace(/</g, "&lt;");
        str = str.replace(/>/g, "&gt;");

        return str;
    },

    htmlDecode: function() {
        if (this == "") {
          return "";
        }

        str = this.replace(/&amp;/g, "&");
        str = str.replace(/&lt;/g, "<");
        str = str.replace(/&gt;/g, ">");

        return str;
    }
};

YAHOO.augment(String, RB.utils.String);


// Taken from http://www.quirksmode.org/viewport/compatibility.html
var getViewportInfo = function() {
    var innerWidth, innerHeight, pageXOffset, pageYOffset;

    // all except Explorer
    if (self.innerHeight) {
        innerWidth = self.innerWidth;
        innerHeight = self.innerHeight;
        pageXOffset = self.pageXOffset;
        pageYOffset = self.pageYOffset;

    // Explorer 6 Strict Mode
    } else if (document.documentElement && document.documentElement.clientHeight) {
        innerWidth = document.documentElement.clientWidth;
        innerHeight = document.documentElement.clientHeight;
        pageXOffset = document.documentElement.scrollLeft;
        pageYOffset = document.documentElement.scrollTop;

    // other Explorers
    } else if (document.body) {
        innerWidth = document.body.clientWidth;
        innerHeight = document.body.clientHeight;
        pageXOffset = document.body.scrollLeft;
        pageYOffset = document.body.scrollTop;
    }

    var pageWidth, pageHeight;
    if (document.body.scrollHeight > document.body.offsetHeight) {
        pageWidth = document.body.scrollWidth;
        pageHeight = document.body.scrollHeight;
    } else {
        pageWidth = document.body.offsetWidth;
        pageHeight = document.body.offsetHeight;
    }

    return {
        innerWidth: innerWidth,
        innerHeight: innerHeight,
        pageXOffset: pageXOffset,
        pageYOffset: pageYOffset,
        pageWidth: pageWidth,
        pageHeight: pageHeight
    };
};


var asyncJsonRequest = function(method, url, callbacks, postData) {
    var onSuccess = function(res) {
        /*
         * When uploading files asynchronously, YUI performs the action in
         * an iframe and the result is loaded like HTML. As such, it ends up
         * with a <pre>..</pre> and entities.
         */
        if (res.responseText.substr(0, 5).toLowerCase() == "<pre>") {
            res.responseText = res.responseText.stripTags().htmlDecode();
        }

        try {
            rsp = YAHOO.ext.util.JSON.decode(res.responseText);
        } catch(e) {
            if (callbacks.failure) {
                /*
                 * Let the user know what happened. It'd be nice to give
                 * a link to the debug output from the request for debugging
                 * purposes.
                 */
                callbacks.failure("Unable to parse the server response");

                if (console) {
                    console.error("Unable to parse the server response.");
                    console.group("Response text");
                    console.debug(res.responseText);
                    console.groupEnd();
                }
            }
            return;
        }

        if (rsp.stat == 'fail') {
            if (callbacks.failure) {
                callbacks.failure(rsp.err.msg, rsp);
            }
        } else if (callbacks.success) {
            callbacks.success(rsp);
        }
    }.createDelegate(this);

    YAHOO.util.Connect.asyncRequest(method, url, {
        success: onSuccess,
        upload: onSuccess,
        failure: function(res) {
            if (callbacks.failure) {
                callbacks.failure(res.statusText);
            }
        }
    }, postData || "dummy");
};


/*
 * Toggles whether an object is starred. Right now, we support
 * "reviewrequests" and "groups" types.
 *
 * @param {HTMLElement} el        The star img element.
 * @param {string}      type      The type used for constructing the path.
 * @param {string}      objid     The object ID to star/unstar.
 * @param {bool}        default_  The default value.
 */
function toggleStar(el, type, objid, default_) {
  var isStarred = gStars[el] == undefined ? default_ : gStars[el];
  var url = "/api/json/" + type + "/" + objid + "/";

  if (isStarred) {
    url += "unstar/";
  } else {
    url += "star/";
  }

  asyncJsonRequest("GET", url, {
    success: function(rsp) {
      if (isStarred) {
        el.src = STAR_OFF_IMG;
      } else {
        el.src = STAR_ON_IMG;
      }

      gStars[el] = !isStarred;
    },
    failure: function(errmsg) {
      alert(errmsg);
    }
  });
}
