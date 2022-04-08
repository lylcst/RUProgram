"use strict";

const PizZipUtils = {};
// just use the responseText with xhr1, response with xhr2.
// The transformation doesn't throw away high-order byte (with responseText)
// because PizZip handles that case. If not used with PizZip, you may need to
// do it, see https://developer.mozilla.org/En/Using_XMLHttpRequest#Handling_binary_data
PizZipUtils._getBinaryFromXHR = function(xhr) {
	// for xhr.responseText, the 0xFF mask is applied by PizZip
	return xhr.response || xhr.responseText;
};

// taken from jQuery
function createStandardXHR() {
	try {
		return new window.XMLHttpRequest();
	} catch (e) {}
}

function createActiveXHR() {
	try {
		return new window.ActiveXObject("Microsoft.XMLHTTP");
	} catch (e) {}
}

// Create the request object
const createXHR = window.ActiveXObject
	? /* Microsoft failed to properly
	   * implement the XMLHttpRequest in IE7 (can't request local files),
	   * so we use the ActiveXObject when it is available
	   * Additionally XMLHttpRequest can be disabled in IE7/IE8 so
	   * we need a fallback.
	   */
	  function() {
			return createStandardXHR() || createActiveXHR();
	  }
	: // For all other browsers, use the standard XMLHttpRequest object
	  createStandardXHR;

PizZipUtils.getBinaryContent = function(path, callback) {
	try {
		const xhr = createXHR();

		xhr.open("GET", path, true);

		// recent browsers
		if ("responseType" in xhr) {
			xhr.responseType = "arraybuffer";
		}

		// older browser
		if (xhr.overrideMimeType) {
			xhr.overrideMimeType("text/plain; charset=x-user-defined");
		}

		xhr.onreadystatechange = function(evt) {
			let file, err;
			// use `xhr` and not `this`... thanks IE
			if (xhr.readyState === 4) {
				if (xhr.status === 200 || xhr.status === 0) {
					file = null;
					err = null;
					try {
						file = PizZipUtils._getBinaryFromXHR(xhr);
					} catch (e) {
						err = new Error(e);
					}
					callback(err, file);
				} else {
					callback(
						new Error(
							"Ajax error for " +
								path +
								" : " +
								this.status +
								" " +
								this.statusText
						),
						null
					);
				}
			}
		};

		xhr.send();
	} catch (e) {
		callback(new Error(e), null);
	}
};
