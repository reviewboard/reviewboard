var checkIfObject;

if (!Object.getPrototypeOf) {
    checkIfObject = function(obj) {
        if (obj !== Object(obj)) {
            throw new TypeError('Object.getPrototypeOf called on non-object');
        }
    };

    if (typeof 'test'.__proto__ === 'object') {
        Object.getPrototypeOf = function(obj) {
            checkIfObject(obj);
            return obj.__proto__;
        };
    } else {
        Object.getPrototypeOf = function(obj) {
            checkIfObject(obj);
            return obj.constructor.prototype;
        };
    }
}
