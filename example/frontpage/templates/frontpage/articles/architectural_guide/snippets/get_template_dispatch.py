def get_template(request: HttpRequest, template_name: str) -> str:
    """Substitutes a full template for its OOB shell on HTMX requests."""
    if request.headers.get("HX-Request", "") == "true":
        name = template_name.rsplit("/", 1)[-1]
        return f"vanilla_htmx_composite/_{name}"
    return template_name