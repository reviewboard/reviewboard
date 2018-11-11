.. _extension-resources:

=====================
Extending the Web API
=====================

Each extension has a very basic API resource that clients can use to fetch
details on the extension, such as the name, URLs, and whether it's enabled.

Extensions can extend this to provide even more resources, which can be used
to retrieve or modify any information the extension chooses. They do this by
creating :py:class:`reviewboard.webapi.resources.WebAPIResource` subclasses
and listing an instance of each that you want as a child of the extension's
resource in :py:attr:`resources` attribute.

Resources are complex, but are explained in detail in the Djblets
`WebAPIResource code`_.

.. _`WebAPIResource code`:
   https://github.com/djblets/djblets/blob/master/djblets/webapi/resources/base.py


For example, a resource for creating and publishing a simplified review may
look like:

.. code-block:: python

   from django.core.exceptions import ObjectDoesNotExist
   from djblets.webapi.decorators import (webapi_login_required,
                                          webapi_response_errors,
                                          webapi_request_fields)
   from djblets.webapi.errors import DOES_NOT_EXIST
   from reviewboard.reviews.models import Review
   from reviewboard.webapi.decorators import webapi_check_local_site
   from reviewboard.webapi.resources import WebAPIResource, resources


   class SampleExtensionResource(WebAPIResource):
       """Resource for creating reviews"""
       name = 'sample_extension_review'
       uri_name = 'review'
       allowed_methods = ('POST',)

       def has_access_permissions(self, request, *args, **kwargs):
           return review_request.is_accessible_by(request.user)

       @webapi_check_local_site
       @webapi_login_required
       @webapi_response_errors(DOES_NOT_EXIST)
       @webapi_request_fields(
           required={
               'review_request_id': {
                   'type': int,
                   'description': 'The ID of the review request',
               },
           },
       )
       def create(self, request, review_request_id, *args, **kwargs):
           try:
               review_request = resources.review_request.get_object(
                   request, review_request_id, *args, **kwargs)
           except ObjectDoesNotExist:
               return DOES_NOT_EXIST

           new_review = Review.objects.create(
               review_request=review_request,
               user=request.user,
               body_top='Sample review body')
           new_review.publish(user=request.user)

           return 201, {
               self.item_result_key: new_review
           }

   sample_review_resource = SampleExtensionResource()


The extension would then make use of this with:

.. code-block:: python

   class SampleExtension(Extension):
       resources = [sample_review_resource]


With this, one would be able to POST to this resource to create reviews that
contained the text "Sample review body". This API endpoint would be registered
at ``/api/extensions/sample_extension.extension.SampleExtension/reviews/``.
