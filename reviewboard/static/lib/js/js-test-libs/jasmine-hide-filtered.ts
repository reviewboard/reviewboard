/**
 * Hide filtered-out specs from view in Jasmine 1.4+.
 *
 * This is a simple drop-in script that restores the Jasmine 1.3.x behavior
 * of hiding any specs not matching the suite path specified in ?spec=<path>.
 * This helps keep the list of results focused when working on a small part of
 * a large test suite.
 */
import {
    Suite,
    jasmine,
} from 'jasmine-core';


const queryString = new jasmine.QueryString({
    getWindowLocation: function() {
        return window.location;
    }
});


/**
 * Hide suites that are filtered out.
 *
 * This will iterate through the children of a suite, looking to see if there
 * are any enabled specs. If not, the suite will be considered hidden.
 *
 * This happens recursively, eventually hiding all suites except those
 * containing enabled specs somewhere in its tree.
 *
 * Args:
 *     suite (jasmine.Suite):
 *         The suite to iterate through.
 *
 * Returns:
 *     boolean:
 *     Whether or not this suite is marked as hidden.
 */
function hideFilteredSuites(
    suite: Suite,
): boolean {
    let hide = true;

    for (const child of suite.children) {
        if ((child.children === undefined && !child.disabled) ||
            (child.children !== undefined && !hideFilteredSuites(child))) {
            hide = false;
        }
    }

    if (hide) {
        /* This suite can be hidden. */
        const el = document.getElementById('suite-' + suite.id);

        if (el) {
            el.setAttribute('style', 'display: none;');
        }
    }

    return hide;
}


/**
 * Add a checkbox for toggling whether filtered-out suites should be hidden.
 *
 * Args:
 *     filterSpecs (boolean):
 *         The current setting for hiding filtered-out suites.
 */
function addFilterCheckbox(
    filterSpecs: boolean,
) {
    const optionsEl = document.getElementsByClassName('jasmine-payload')[0];
    const checkboxContainerEl = document.createElement('div');
    const checkboxEl = document.createElement('input');
    checkboxEl.setAttribute('type', 'checkbox');
    checkboxEl.setAttribute('id', 'jasmine-hide-filtered');
    checkboxContainerEl.appendChild(checkboxEl);

    if (filterSpecs) {
        checkboxEl.setAttribute('checked', 'checked');
    }

    const labelEl = document.createElement('label');
    labelEl.className = 'jasmine-label';
    labelEl.setAttribute('for', 'jasmine-hide-filtered');
    labelEl.appendChild(document.createTextNode('hide filtered suites'));
    checkboxContainerEl.appendChild(labelEl);

    optionsEl.appendChild(checkboxContainerEl);

    checkboxEl.addEventListener('change', function() {
        queryString.navigateWithNewParam(
            'filter-specs',
            filterSpecs ? 'false' : 'true');
    });
}


window.addEventListener('DOMContentLoaded', function() {
    jasmine.getEnv().addReporter({
        jasmineDone: function() {
            const spec = queryString.getParam('spec');
            const filterSpecs = (queryString.getParam('filter-specs') !== false);

            addFilterCheckbox(filterSpecs);

            if (spec && spec.length > 0 && filterSpecs) {
                hideFilteredSuites(jasmine.getEnv().topSuite());
            }
        }
    });
}, false);
