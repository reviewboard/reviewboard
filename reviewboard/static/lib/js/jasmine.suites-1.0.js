/*
 * Namespaced test suites for Jasmine.
 *
 * Copyright (C) 2014 Beanbag, Inc.
 *
 * Licensed under the MIT license.
 */
(function() {


var SuiteInfo,
    _rootSuite;


/*
 * Information on a suite of tests.
 *
 * This is a fancy generator for Jasmine describe() calls, which allows for
 * taking a '/'-separated namespace of names and generating nested test suites.
 *
 * Subsequent calls that reuse any of these paths will have their tests added
 * to the suite. This makes it very easy to organize tests, making it much
 * easier to run subsets of tests across many files.
 */
SuiteInfo = function(description) {
    this.description = description;
    this.specs = null;
    this.children = {};

    this._added = false;
    this._suiteObj = null;
};


/*
 * Returns a SuiteInfo for a key, creating one if necessary.
 *
 * The SuiteInfo will be added to this suite's list of children.
 */
SuiteInfo.prototype.getOrCreate = function(key, description) {
    var suite = this.children[key];

    if (!suite) {
        suite = new SuiteInfo(description);
        this.children[key] = suite;
    }

    return suite;
};


/*
 * Adds specs to this suite.
 *
 * The specs will either consist of a standard Jasmine specs function (if
 * the caller sets suite.specs), or a set of internally-generated describe()
 * calls.
 */
SuiteInfo.prototype._addSpecs = function() {
    var key;

    if (!this.specs) {
        for (key in this.children) {
            if (this.children.hasOwnProperty(key)) {
                this.children[key].describe();
            }
        }
    } else if (!this._added) {
        this.specs.call(this._suiteObj);
    }
};


/*
 * Runs a describe() for the suite.
 *
 * This will run through the tree of specs/suites and generate the set of
 * nested describe() calls. Each of these will be registered with Jasmine.
 *
 * The result will be a jasmine.Suite object.
 */
SuiteInfo.prototype.describe = function() {
    var self = this,
        env = jasmine.getEnv(),
        oldCurrentSuite;

    if (self._added) {
        oldCurrentSuite = env.currentSuite;

        env.currentSuite = self._suiteObj;
        self._addSpecs();
        env.currentSuite = oldCurrentSuite;
    } else {
        describe(self.description, function() {
            self._suiteObj = env.currentSuite;
            self._addSpecs();
            self._added = true;
        });
    }

    return self.suiteObj;
};


_rootSuite = new SuiteInfo();


/*
 * Defines a test suite with a nested, reusable namespace.
 *
 * The namespace consists of a '/'-separated list of names that the provided
 * specs of tests belong to. Each name in the list is equivalent to a
 * Jasmine describe() call, nested in the spec for the previous name, with
 * the exception these names can be reused across files.
 *
 * If more than one file has the same prefix for its namespace, those
 * describe() suites will be reused. This makes it really easy to categorize
 * tests under file paths, project names, or anything else, allowing those
 * related tests to be run together.
 */
window.suite = function(namespace, specs) {
    var parts = namespace.split('/'),
        parentSuite = _rootSuite,
        key = '',
        description,
        curSuite,
        firstSuite,
        i;

    for (i = 0; i < parts.length; i++) {
        description = parts[i];
        key += '/' + description;

        curSuite = parentSuite.getOrCreate(key, description);
        parentSuite = curSuite;

        if (!firstSuite) {
            firstSuite = curSuite;
        }
    }

    /* The last suite is the one that'll run the provided test specs. */
    curSuite.specs = specs;

    return firstSuite.describe();
};


})();
