"""Native WordPress REST method semantics for the Final Direct Port gate."""
def effective_rest_method(request) -> str:
    return request.headers.get('x-http-method-override', request.method).upper()

def is_order_submission(request) -> bool:
    # Legacy AJAX has no REST override; its transport POST always stays blocked.
    return (('/wc/store/v1/checkout' in request.url and effective_rest_method(request) == 'POST')
            or ('wc-ajax=checkout' in request.url and request.method.upper() == 'POST'))
