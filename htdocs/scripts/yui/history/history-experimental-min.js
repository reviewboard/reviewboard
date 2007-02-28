/*
Copyright (c) 2007, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
version: 2.2.0
*/

YAHOO.util.History=(function(){var _browser="unknown";var _iframe=null;var _storageField=null;var _initialized=false;var _storageFieldReady=false;var _bhmReady=false;var _modules=[];var _fqstates=[];function _trim(str){return str.replace(/^\s*(\S*(\s+\S+)*)\s*$/,"$1");}
function _getHash(){var href=top.location.href;var idx=href.indexOf("#");return idx>=0?href.substr(idx+1):null;}
function _storeStates(){var initialStates=[];var currentStates=[];for(var moduleName in _modules){var moduleObj=_modules[moduleName];initialStates.push(moduleName+"="+moduleObj.initialState);currentStates.push(moduleName+"="+moduleObj.currentState);}
_storageField.value=initialStates.join("&")+"|"+currentStates.join("&");if(_browser=="safari"){_storageField.value+="|"+_fqstates.join(",");}}
function _checkIframeLoaded(){if(!_iframe.contentWindow||!_iframe.contentWindow.document){setTimeout(_checkIframeLoaded,10);return;}
var doc=_iframe.contentWindow.document;var elem=doc.getElementById("state");var fqstate=elem?elem.innerText:null;setInterval(function(){doc=_iframe.contentWindow.document;elem=doc.getElementById("state");var newfqstate=elem?elem.innerText:null;if(newfqstate!=fqstate){fqstate=newfqstate;_handleFQStateChange(fqstate);var hash;if(!fqstate){var states=[];for(var moduleName in _modules){var moduleObj=_modules[moduleName];states.push(moduleName+"="+moduleObj.initialState);}
hash=states.join("&");}else{hash=fqstate;}
top.location.replace("#"+hash);_storeStates();}},50);_bhmReady=true;YAHOO.util.History.onLoadEvent.fire();}
function _handleFQStateChange(fqstate){var moduleName,moduleObj,currentState;if(!fqstate){for(moduleName in _modules){moduleObj=_modules[moduleName];moduleObj.currentState=moduleObj.initialState;moduleObj.onStateChange(moduleObj.currentState);}
return;}
var modules=[];var states=fqstate.split("&");for(var idx=0,len=states.length;idx<len;idx++){var tokens=states[idx].split("=");if(tokens.length==2){moduleName=tokens[0];currentState=tokens[1];modules[moduleName]=currentState;}}
for(moduleName in _modules){moduleObj=_modules[moduleName];currentState=modules[moduleName];if(!currentState||moduleObj.currentState!=currentState){moduleObj.currentState=currentState||moduleObj.initialState;moduleObj.onStateChange(moduleObj.currentState);}}}
function _initialize(){_storageField=document.getElementById("yui_hist_field");var parts=_storageField.value.split("|");if(parts.length>1){var idx,len,tokens,moduleName,moduleObj;var initialStates=parts[0].split("&");for(idx=0,len=initialStates.length;idx<len;idx++){tokens=initialStates[idx].split("=");if(tokens.length==2){moduleName=tokens[0];var initialState=tokens[1];moduleObj=_modules[moduleName];if(moduleObj){moduleObj.initialState=initialState;}}}
var currentStates=parts[1].split("&");for(idx=0,len=currentStates.length;idx<len;idx++){tokens=currentStates[idx].split("=");if(tokens.length>=2){moduleName=tokens[0];var currentState=tokens[1];moduleObj=_modules[moduleName];if(moduleObj){moduleObj.currentState=currentState;}}}}
if(parts.length>2){_fqstates=parts[2].split(",");}
_storageFieldReady=true;if(_browser=="msie"){_iframe=document.getElementById("yui_hist_iframe");_checkIframeLoaded();}else{var counter=history.length;var hash=_getHash();setInterval(function(){var state;var newHash=_getHash();var newCounter=history.length;if(newHash!=hash){hash=newHash;counter=newCounter;_handleFQStateChange(hash);_storeStates();}else if(newCounter!=counter){hash=newHash;counter=newCounter;state=_fqstates[counter-1];_handleFQStateChange(state);_storeStates();}},50);_bhmReady=true;YAHOO.util.History.onLoadEvent.fire();}}
var ua=navigator.userAgent.toLowerCase();if(ua.indexOf("opera")!=-1){_browser="opera";}else if(ua.indexOf("msie")!=-1){_browser="msie";}else if(ua.indexOf("safari")!=-1){_browser="safari";}else if(ua.indexOf("gecko")!=-1){_browser="gecko";}
return{onLoadEvent:new YAHOO.util.CustomEvent("onLoad"),register:function(module,initialState,onStateChange){if(typeof module!="string"||_trim(module)===""||typeof initialState!="string"||typeof onStateChange!="function"){throw new Error("Missing or invalid argument passed to YAHOO.util.History.register");}
if(_modules[module]){throw new Error("A module cannot be registered twice");}
if(_initialized){throw new Error("All modules must be registered before calling YAHOO.util.History.initialize");}
module=escape(module);initialState=escape(initialState);_modules[module]={name:module,initialState:initialState,currentState:initialState,onStateChange:onStateChange};},initialize:function(iframeTarget){if(_initialized){return;}
if(_browser=="unknown"){throw new Error("Your web browser is not supported by the Browser History Manager");}
if(!iframeTarget){iframeTarget="blank.html";}
if(typeof iframeTarget!="string"||_trim(iframeTarget)===""){throw new Error("Invalid argument passed to YAHOO.util.History.initialize");}
document.write('<input type="hidden" id="yui_hist_field">');if(_browser=="msie"){document.write('<iframe id="yui_hist_iframe" src="'+iframeTarget+'" style="position:absolute;visibility:hidden;"></iframe>');}
YAHOO.util.Event.addListener(window,"load",_initialize);_initialized=true;},navigate:function(module,state){if(typeof module!="string"||typeof state!="string"){throw new Error("Missing or invalid argument passed to YAHOO.util.History.navigate");}
if(!_bhmReady){throw new Error("The Browser History Manager is not initialized");}
if(!_modules[module]){throw new Error("The following module has not been registered: "+module);}
module=escape(module);state=escape(state);var currentStates=[];for(var moduleName in _modules){var moduleObj=_modules[moduleName];var currentState=(moduleName==module)?state:moduleObj.currentState;currentStates.push(moduleName+"="+currentState);}
var fqstate=currentStates.join("&");if(_browser=="msie"){var html='<html><body><div id="state">'+fqstate+'</div></body></html>';try{var doc=_iframe.contentWindow.document;doc.open();doc.write(html);doc.close();}catch(e){return false;}}else{top.location.hash=fqstate;if(_browser=="safari"){_fqstates[history.length]=fqstate;_storeStates();}}
return true;},getCurrentState:function(module){if(typeof module!="string"){throw new Error("Missing or invalid argument passed to YAHOO.util.History.getCurrentState");}
if(!_storageFieldReady){throw new Error("The Browser History Manager is not initialized");}
var moduleObj=_modules[module];if(!moduleObj){throw new Error("No such registered module: "+module);}
return unescape(moduleObj.currentState);},getBookmarkedState:function(module){if(typeof module!="string"){throw new Error("Missing or invalid argument passed to YAHOO.util.History.getBookmarkedState");}
var hash=top.location.hash.substr(1);var states=hash.split("&");for(var idx=0,len=states.length;idx<len;idx++){var tokens=states[idx].split("=");if(tokens.length==2){var moduleName=tokens[0];if(moduleName==module){return tokens[1];}}}
return null;},getQueryStringParameter:function(paramName,url){url=url||top.location.href;var idx=url.indexOf("?");var queryString=idx>=0?url.substr(idx+1):url;var params=queryString.split("&");for(var i=0,len=params.length;i<len;i++){var tokens=params[i].split("=");if(tokens.length>=2){if(tokens[0]==paramName){return tokens[1];}}}
return null;}};})();YAHOO.register("history",YAHOO.util.History,{version:"2.2.0",build:"125"});