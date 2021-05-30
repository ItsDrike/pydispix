def resolve_url_endpoint(base_url: str, endpoint_url: str) -> str:
    """Add `endpoint_url` to the `base_url` and return the whole URL"""
    if endpoint_url.startswith("/"):
        endpoint_url = endpoint_url[1:]
    if endpoint_url.startswith("https://") or endpoint_url.startswith("http://"):
        if endpoint_url.startswith(base_url):
            return endpoint_url
        raise ValueError("`endpoint` referrs to unknown full url, that doesn't belong to the base url")
    else:
        return base_url + endpoint_url
