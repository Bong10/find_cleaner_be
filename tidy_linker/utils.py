from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If the response is None, it means it's an unhandled exception (like 500)
    # We let Django handle those (or you could handle them here too)
    if response is not None:
        
        # Initialize our unified error message
        error_message = "An error occurred."
        
        # Case 1: "detail" (Standard DRF errors like 401, 403, 404)
        if "detail" in response.data:
            error_message = response.data["detail"]
            
        # Case 2: "non_field_errors" (General validation errors)
        elif "non_field_errors" in response.data:
            # Usually a list, take the first one
            errors = response.data["non_field_errors"]
            error_message = errors[0] if isinstance(errors, list) and errors else str(errors)
            
        # Case 3: Field-specific validation errors (e.g. {"email": ["Invalid"], "password": ["Required"]})
        else:
            # We'll construct a message from the first field error we find
            # Or you could join them all. Let's take the first one for simplicity.
            first_field = next(iter(response.data))
            first_error = response.data[first_field]
            
            if isinstance(first_error, list):
                first_error_msg = first_error[0]
            else:
                first_error_msg = str(first_error)
                
            # Format: "Cleaning supplies: Invalid choice"
            readable_field = first_field.replace('_', ' ').capitalize()
            error_message = f"{readable_field}: {first_error_msg}"

        # Replace the entire data with our unified structure
        # You can keep the original data in a separate field if you want debugging info
        response.data = {
            "errormessage": error_message,
            # Optional: keep original errors for detailed field highlighting if needed
            # "details": response.data 
        }

    return response
