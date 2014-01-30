.. webapi-error::
   :title: Diff Too Big
   :instance: reviewboard.webapi.errors.DIFF_TOO_BIG
   :example-data:
       {
           "reason": "The supplied diff file is too large",
           "max_size": 200000
       }

   A diff was uploaded that was too large to process. The size limit may
   vary between servers.

   The specific reason it failed is provided in ``reason``, and the
   maximum diff size in bytes is provided in ``max_size``.
