"""Errors for actions app.

Version Added:
    6.0
"""


class DepthLimitExceededError(ValueError):
    """An error that occurs when the maximum depth limit is exceeded.

    Actions cannot be arbitrarily nested. For example, if the depth limit is 2,
    then this error would be triggered if an extension tried to add a menu
    action as follows:

    .. code-block:: python

       ActionHook(self, actions=[
           DepthZeroMenuAction(),
           DepthOneFirstItemAction(),
           DepthOneMenuAction(),
           DepthTwoMenuAction(),  # This depth is acceptable.
           DepthThreeTooDeepAction(),  # This action is too deep.
       ])

    Version Added:
        6.0
    """

    def __init__(
        self,
        action_id: str,
        *,
        depth_limit: int,
    ) -> None:
        """Initialize the error.

        Args:
            action_id (str):
                The ID of the action which was too deep.

            depth_limit (int):
                The maximum depth which was exceeded.
        """
        super().__init__('%s exceeds the maximum depth limit of %d'
                         % (action_id, depth_limit))
