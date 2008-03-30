/*
Copyright (c) 2007, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
version: 2.2.0
*/

YAHOO.util.DataSource=function(oLiveData,oConfigs){if(typeof oConfigs=="object"){for(var sConfig in oConfigs){if(sConfig){this[sConfig]=oConfigs[sConfig];}}}
if(!oLiveData){return;}
else{switch(oLiveData.constructor){case Function:this.dataType=YAHOO.util.DataSource.TYPE_JSFUNCTION;break;case Array:this.dataType=YAHOO.util.DataSource.TYPE_JSARRAY;break;case String:this.dataType=YAHOO.util.DataSource.TYPE_XHR;break;case Object:this.dataType=YAHOO.util.DataSource.TYPE_JSON;break;default:this.dataType=YAHOO.util.DataSource.TYPE_UNKNOWN;break;}
this.liveData=oLiveData;}
var maxCacheEntries=this.maxCacheEntries;if(isNaN(maxCacheEntries)||(maxCacheEntries<0)){maxCacheEntries=0;}
if(maxCacheEntries>0&&!this._aCache){this._aCache=[];}
this._sName="instance"+YAHOO.util.DataSource._nIndex;YAHOO.util.DataSource._nIndex++;this.createEvent("cacheRequestEvent");this.createEvent("cacheResponseEvent");this.createEvent("requestEvent");this.createEvent("responseEvent");this.createEvent("responseParseEvent");this.createEvent("responseCacheEvent");this.createEvent("dataErrorEvent");this.createEvent("cacheFlushEvent");};YAHOO.augment(YAHOO.util.DataSource,YAHOO.util.EventProvider);YAHOO.util.DataSource.TYPE_UNKNOWN=-1;YAHOO.util.DataSource.TYPE_JSARRAY=0;YAHOO.util.DataSource.TYPE_JSFUNCTION=1;YAHOO.util.DataSource.TYPE_XHR=2;YAHOO.util.DataSource.TYPE_JSON=3;YAHOO.util.DataSource.TYPE_XML=4;YAHOO.util.DataSource.TYPE_TEXT=5;YAHOO.util.DataSource.ERROR_DATAINVALID="Invalid data";YAHOO.util.DataSource.ERROR_DATANULL="Null data";YAHOO.util.DataSource._nIndex=0;YAHOO.util.DataSource.prototype._sName=null;YAHOO.util.DataSource.prototype._aCache=null;YAHOO.util.DataSource.prototype.maxCacheEntries=0;YAHOO.util.DataSource.prototype.liveData=null;YAHOO.util.DataSource.prototype.connTimeout=null;YAHOO.util.DataSource.prototype.connMgr=YAHOO.util.Connect||null;YAHOO.util.DataSource.prototype.dataType=YAHOO.util.DataSource.TYPE_UNKNOWN;YAHOO.util.DataSource.prototype.responseType=YAHOO.util.DataSource.TYPE_UNKNOWN;YAHOO.util.DataSource.prototype.toString=function(){return"DataSource "+this._sName;};YAHOO.util.DataSource.prototype.getCachedResponse=function(oRequest,oCallback,oCaller){var aCache=this._aCache;var nCacheLength=(aCache)?aCache.length:0;var oResponse=null;if((this.maxCacheEntries>0)&&aCache&&(nCacheLength>0)){this.fireEvent("cacheRequestEvent",{request:oRequest,callback:oCallback,caller:oCaller});for(var i=nCacheLength-1;i>=0;i--){var oCacheElem=aCache[i];if(this.isCacheHit(oRequest,oCacheElem.request)){oResponse=oCacheElem.response;aCache.splice(i,1);this.addToCache(oRequest,oResponse);this.fireEvent("cacheResponseEvent",{request:oRequest,response:oResponse,callback:oCallback,caller:oCaller});break;}}}
return oResponse;};YAHOO.util.DataSource.prototype.isCacheHit=function(oRequest,oCachedRequest){return(oRequest===oCachedRequest);};YAHOO.util.DataSource.prototype.addToCache=function(oRequest,oResponse){var aCache=this._aCache;if(!aCache||!oRequest||!oResponse){return;}
while(aCache.length>=this.maxCacheEntries){aCache.shift();}
var oCacheElem={request:oRequest,response:oResponse};aCache.push(oCacheElem);this.fireEvent("responseCacheEvent",{request:oRequest,response:oResponse});};YAHOO.util.DataSource.prototype.flushCache=function(){if(this._aCache){this._aCache=[];}
this.fireEvent("cacheFlushEvent");};YAHOO.util.DataSource.prototype.sendRequest=function(oRequest,oCallback,oCaller){var oCachedResponse=this.getCachedResponse(oRequest,oCallback,oCaller);if(oCachedResponse){oCallback.call(oCaller,oRequest,oCachedResponse);return;}
this.makeConnection(oRequest,oCallback,oCaller);};YAHOO.util.DataSource.prototype.makeConnection=function(oRequest,oCallback,oCaller){this.fireEvent("requestEvent",{request:oRequest,callback:oCallback,caller:oCaller});var oRawResponse=null;switch(this.dataType){case YAHOO.util.DataSource.TYPE_JSARRAY:case YAHOO.util.DataSource.TYPE_JSON:oRawResponse=this.liveData;this.handleResponse(oRequest,oRawResponse,oCallback,oCaller);break;case YAHOO.util.DataSource.TYPE_JSFUNCTION:oRawResponse=this.liveData(oRequest);this.handleResponse(oRequest,oRawResponse,oCallback,oCaller);break;case YAHOO.util.DataSource.TYPE_XHR:var _xhrSuccess=function(oResponse){if(!oResponse){this.fireEvent("dataErrorEvent",{request:oRequest,callback:oCallback,caller:oCaller,message:YAHOO.util.DataSource.ERROR_DATANULL});return null;}
else if(!this._oConn||(oResponse.tId!=this._oConn.tId)){this.fireEvent("dataErrorEvent",{request:oRequest,callback:oCallback,caller:oCaller,message:YAHOO.util.DataSource.ERROR_DATAINVALID});return null;}
else{this.handleResponse(oRequest,oResponse,oCallback,oCaller);}};var _xhrFailure=function(oResponse){this.fireEvent("dataErrorEvent",{request:oRequest,callback:oCallback,caller:oCaller,message:YAHOO.util.DataSource.ERROR_DATAXHR});return null;};var _xhrCallback={success:_xhrSuccess,failure:_xhrFailure,scope:this};if(this.connTimeout&&!isNaN(this.connTimeout)&&this.connTimeout>0){_xhrCallback.timeout=this.connTimeout;}
if(this._oConn&&this.connMgr){this.connMgr.abort(this._oConn);}
var sUri=this.liveData+"?"+oRequest;if(this.connMgr){this._oConn=this.connMgr.asyncRequest("GET",sUri,_xhrCallback,null);}
else{}
break;default:break;}};YAHOO.util.DataSource.prototype.handleResponse=function(oRequest,oRawResponse,oCallback,oCaller){this.fireEvent("responseEvent",{request:oRequest,response:oRawResponse,callback:oCallback,caller:oCaller});var xhr=(this.dataType==YAHOO.util.DataSource.TYPE_XHR)?true:false;var oParsedResponse=null;switch(this.responseType){case YAHOO.util.DataSource.TYPE_JSARRAY:if(xhr&&oRawResponse.responseText){oRawResponse=oRawResponse.responseText;}
oParsedResponse=this.parseArrayData(oRequest,oRawResponse);break;case YAHOO.util.DataSource.TYPE_JSON:if(xhr&&oRawResponse.responseText){oRawResponse=oRawResponse.responseText;}
oParsedResponse=this.parseJSONData(oRequest,oRawResponse);break;case YAHOO.util.DataSource.TYPE_XML:if(xhr&&oRawResponse.responseXML){oRawResponse=oRawResponse.responseXML;}
oParsedResponse=this.parseXMLData(oRequest,oRawResponse);break;case YAHOO.util.DataSource.TYPE_TEXT:if(xhr&&oRawResponse.responseText){oRawResponse=oRawResponse.responseText;}
oParsedResponse=this.parseTextData(oRequest,oRawResponse);break;default:break;}
if(oParsedResponse){this.fireEvent("responseParseEvent",{request:oRequest,response:oParsedResponse,callback:oCallback,caller:oCaller});this.addToCache(oRequest,oParsedResponse);}
else{this.fireEvent("dataErrorEvent",{request:oRequest,callback:oCallback,caller:oCaller,message:YAHOO.util.DataSource.ERROR_DATANULL});}
oCallback.call(oCaller,oRequest,oParsedResponse);};YAHOO.util.DataSource.prototype.parseArrayData=function(oRequest,oRawResponse){var oParsedResponse=[];var fields=this.responseSchema.fields;for(var i=oRawResponse.length-1;i>-1;i--){var oResult={};for(var j=fields.length;j>-1;j--){oResult[fields[j]]=oRawResponse[i][j]||oRawResponse[i][fields[j]];}
oParsedResponse.unshift(oResult);}
return oParsedResponse;};YAHOO.util.DataSource.prototype.parseTextData=function(oRequest,oRawResponse){var oParsedResponse=[];var recDelim=this.responseSchema.recordDelim;var fieldDelim=this.responseSchema.fieldDelim;var aSchema=this.responseSchema.fields;if(oRawResponse.length>0){var newLength=oRawResponse.length-recDelim.length;if(oRawResponse.substr(newLength)==recDelim){oRawResponse=oRawResponse.substr(0,newLength);}
var recordsarray=oRawResponse.split(recDelim);for(var i=recordsarray.length-1;i>=1;i--){var dataobject={};for(var j=aSchema.length-1;j>=0;j--){var fielddataarray=recordsarray[i].split(fieldDelim);var string=fielddataarray[j];if(string.charAt(0)=="\""){string=string.substr(1);}
if(string.charAt(string.length-1)=="\""){string=string.substr(0,string.length-1);}
dataobject[aSchema[j]]=string;}
oParsedResponse.push(dataobject);}}
return oParsedResponse;};YAHOO.util.DataSource.prototype.parseXMLData=function(oRequest,oRawResponse){var bError=false;var oParsedResponse=[];var xmlList=oRawResponse.getElementsByTagName(this.responseSchema.resultNode);if(!xmlList){bError=true;}
else{for(var k=xmlList.length-1;k>=0;k--){var result=xmlList.item(k);var oResult={};for(var m=this.responseSchema.fields.length-1;m>=0;m--){var field=this.responseSchema.fields[m];var sValue=null;var xmlAttr=result.attributes.getNamedItem(field);if(xmlAttr){sValue=xmlAttr.value;}
else{var xmlNode=result.getElementsByTagName(field);if(xmlNode&&xmlNode.item(0)&&xmlNode.item(0).firstChild){sValue=xmlNode.item(0).firstChild.nodeValue;}
else{sValue="";}}
oResult[field]=sValue;}
oParsedResponse.unshift(oResult);}}
if(bError){return null;}
return oParsedResponse;};YAHOO.util.DataSource.prototype.parseJSONData=function(oRequest,oRawResponse){var bError=false;var oParsedResponse=[];var aSchema=this.responseSchema.fields;var jsonObj,jsonList;if(oRawResponse){if(oRawResponse.constructor==String){if(oRawResponse.parseJSON&&(navigator.userAgent.toLowerCase().indexOf('khtml')==-1)){jsonObj=oRawResponse.parseJSON();if(!jsonObj){bError=true;}}
else if(window.JSON&&JSON.parse&&(navigator.userAgent.toLowerCase().indexOf('khtml')==-1)){jsonObj=JSON.parse(oRawResponse);if(!jsonObj){bError=true;}}
else{try{while(oRawResponse.length>0&&(oRawResponse.charAt(0)!="{")&&(oRawResponse.charAt(0)!="[")){oRawResponse=oRawResponse.substring(1,oResponse.length);}
if(oRawResponse.length>0){var objEnd=Math.max(oRawResponse.lastIndexOf("]"),oRawResponse.lastIndexOf("}"));oRawResponse=oRawResponse.substring(0,objEnd+1);jsonObj=eval("("+oRawResponse+")");if(!jsonObj){bError=true;}}}
catch(e){bError=true;}}}
else if(oRawResponse.constructor==Object){jsonObj=oRawResponse;}
if(jsonObj&&jsonObj.constructor==Object){try{jsonList=eval("jsonObj."+this.responseSchema.resultsList);}
catch(e){bError=true;}}}
if(bError||!jsonList){return null;}
if(jsonList.constructor!=Array){jsonList=[jsonList];}
for(var i=jsonList.length-1;i>=0;i--){var oResult={};var jsonResult=jsonList[i];for(var j=aSchema.length-1;j>=0;j--){var dataFieldValue=jsonResult[aSchema[j]];if(!dataFieldValue){dataFieldValue="";}
oResult[aSchema[j]]=dataFieldValue;}
oParsedResponse.unshift(oResult);}
return oParsedResponse;};YAHOO.register("datasource",YAHOO.util.DataSource,{version:"2.2.0",build:"125"});