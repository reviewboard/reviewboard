/**
 * Return the location hash in a safe manner.
 *
 * If the hash does not look like it can be trusted, we will instead return
 * the empty string.
 *
 * Args:
 *     url (string, optional):
 *         An optional URL to parse the hash out of. If not provided,
 *         ``window.location.href`` is used instead.
 *
 * Returns:
 *     string:
 *     The location hash.
 */
RB.getLocationHash = function(url) {
    if (url === undefined) {
        url = window.location.href;
    }

    const rawHash = url.split('#')[1] || '';
    const decodedHash = decodeURIComponent(rawHash);

    if (!decodedHash.match(/^[A-Za-z0-9,_\.-]*$/)) {
        /*
         * This hash contains characters we cannot necessarily trust.
         * Instead of hoping we can trust it or attempting to sanitize it,
         * we are going to ignore it.
         */
        console.warn('Ignoring location hash "%s".', rawHash);
        return '';
    }

    return decodedHash;
};
