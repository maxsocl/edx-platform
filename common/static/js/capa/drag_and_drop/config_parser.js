// Wrapper for RequireJS. It will make the standard requirejs(), require(), and
// define() functions from Require JS available inside the anonymous function.
//
// See https://edx-wiki.atlassian.net/wiki/display/LMS/Integration+of+Require+JS+into+the+system
(function (requirejs, require, define) {

define(['logme'], function (logme) {
    return configParser;

    function configParser(config, imageDir, state) {
        var returnStatus;

        returnStatus = true;

        state.config = {
            'imageDir': '/static/' + imageDir + '/images',
            'draggable': [],
            'targets': [],
            'target_container': ''
        };

        if ($.isArray(config.draggable) === true) {
            (function (i) {
                while (i < config.draggable.length) {
                    if (processDraggable(config.draggable[i]) !== true) {
                        returnStatus = false;
                    }
                    i += 1;
                }
            }(0));
        } else if ($.isPlainObject(config.draggable) === true) {
            if (processDraggable(config.draggable) !== true) {
                returnStatus = false;
            }
        } else {
            logme('ERROR: The type of config.draggable is no supported.');
            returnStatus = false;
        }

        if (typeof config.target_container === 'string') {
            state.config.target_container = config.target_container;
        } else {
            logme('ERROR: Property config.target_container is not of type "string".');
            returnStatus = false;
        }

        if ($.isArray(config.targets) === true) {
            (function (i) {
                while (i < config.targets.length) {
                    if (processTarget(config.targets[i]) !== true) {
                        returnStatus = false;
                    }
                    i += 1;
                }
            }(0));
        } else if ($.isPlainObject(config.targets) === true) {
            if (processTarget(config.targets) !== true) {
                returnStatus = false;
            }
        } else if (typeof config.targets !== 'undefined') {
            logme('ERROR: Property config.targets is not of a supported type.');
            returnStatus = false;
        }

        if (typeof config.one_per_target === 'string') {
            if (config.one_per_target.toLowerCase() === 'true') {
                state.config.one_per_target = true;
            } else if (config.one_per_target.toLowerCase() === 'false') {
                state.config.one_per_target = false;
            } else {
                logme('ERROR: Property config.one_per_target can either be "true", or "false".');
                returnStatus = false;
            }
        } else if (typeof config.one_per_target !== 'undefined') {
            logme('ERROR: Property config.one_per_target is not of a supported type.');
            returnStatus = false;
        }

        if (typeof config.target_outline === 'string') {
            if (config.target_outline.toLowerCase() === 'true') {
                state.config.target_outline = true;
            } else if (config.target_outline.toLowerCase() === 'false') {
                state.config.target_outline = false;
            } else {
                logme('ERROR: Property config.target_outline can either be "true", or "false".');
                returnStatus = false;
            }
        } else if (typeof config.target_outline !== 'undefined') {
            logme('ERROR: Property config.target_outline is not of a supported type.');
            returnStatus = false;
        }

        if (state.config.targets.length === 0) {
            state.individualTargets = false;
        } else {
            state.individualTargets = true;
        }

        return true;

        function processDraggable(obj) {
            if (!attrIsString(obj, 'id')) { return false; }

            if (!attrIsString(obj, 'icon')) { return false; }
            if (!attrIsString(obj, 'label')) { return false; }

            state.config.draggable.push(obj);

            true;
        }

        function processTarget(obj) {
            if (!attrIsString(obj, 'id')) { return false; }

            if (!attrIsInteger(obj, 'w')) { return false; }
            if (!attrIsInteger(obj, 'h')) { return false; }

            if (!attrIsInteger(obj, 'x')) { return false; }
            if (!attrIsInteger(obj, 'y')) { return false; }

            state.config.targets.push(obj);

            true;

        }

        function attrIsString(obj, attr) {
            if (typeof obj[attr] !== 'string') {
                logme('ERROR: Attribute "obj.' + attr + '" is not a string.');

                return false;
            }

            return true;
        }

        function attrIsInteger(obj, attr) {
            var tempInt;

            tempInt = parseInt(obj[attr], 10);

            if (isFinite(tempInt) === false) {
                logme('ERROR: Attribute "obj.' + attr + '" is not an integer.');

                return false;
            }

            obj[attr] = tempInt;

            return true;
        }
    }
});

// End of wrapper for RequireJS. As you can see, we are passing
// namespaced Require JS variables to an anonymous function. Within
// it, you can use the standard requirejs(), require(), and define()
// functions as if they were in the global namespace.
}(RequireJS.requirejs, RequireJS.require, RequireJS.define)); // End-of: (function (requirejs, require, define)
