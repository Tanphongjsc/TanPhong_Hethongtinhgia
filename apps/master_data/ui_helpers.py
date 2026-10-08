"""Request/form presentation helpers reused by the implemented slices."""
from django.shortcuts import redirect


def is_htmx(request):
    return request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"


def add_form_error(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


def saved_response(request, destination):
    response = redirect(destination)
    if is_htmx(request):
        response.status_code = 200
        response["HX-Redirect"] = destination
    return response
