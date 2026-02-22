/*
 * Alias the Djblets extension framework into the RB namespace.
 *
 * This provides a nice consistency, so that extensions don't have to refer to
 * Djblets. It also makes it easier down the road for us to subclass and
 * provide new functionality for these classes without extensions having to
 * update to use the new names.
 */
RB.Extension = Djblets.Extension;
RB.ExtensionHook = Djblets.ExtensionHook;
RB.ExtensionHookPoint = Djblets.ExtensionHookPoint;
