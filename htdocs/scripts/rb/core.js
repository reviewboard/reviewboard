RB = {utils: {}}

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


var asyncJsonRequest = function(method, url, callbacks) {
  YAHOO.util.Connect.asyncRequest(method, url, {
    success: function(res) {
      rsp = YAHOO.ext.util.JSON.decode(res.responseText);

      if (rsp.stat == 'fail') {
        if (callbacks.failure) {
          callbacks.failure(rsp.err.msg, rsp);
        }
      } else {
        if (callbacks.success) {
          callbacks.success(rsp);
        }
      }
    }.createDelegate(this),

    failure: function(res) {
      if (callbacks.failure) {
        callbacks.failure(res.statusText);
      }
    }
  });
};
