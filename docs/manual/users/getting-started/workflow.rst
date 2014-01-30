================
General Workflow
================

The general process for using Review Board is as follows:

1. Make a change to your local source tree.
2. :ref:`Create a review request <creating-review-requests>` for your new
   change.
3. Publish the review request and wait for your reviewers to see it.
4. Wait for feedback from the reviewers.
5. If they're ready for it to go in:

   1. Submit your change to the repository.
   2. Click :menuselection:`Close --> Submitted` on the review request
      action bar.
6. If they've requested changes:

   1. Update the code in your tree and generate a new diff.
   2. Upload the new diff, specify the changes in the Change Description box,
      and publish.
   3. Jump back to step 4.

This workflow assumes a :term:`pre-commit review` model.
:term:`post-commit review` and decentralized version control models may be
different. If you're unsure about your process, talk to your system
administrator for detailed instructions.


.. comment: vim: ft=rst et
