try:  # Python 3.8
    from functools import cached_property
except ImportError:
    try:  # When nbviewer fork gets merged into master
        from nbviewer.utils import cached_property
    except ImportError:
        from functools import lru_cache

        def cached_property(method):
            return property(lru_cache(1)(method))


try:
    from nbviewer.utils import response_text
except ImportError:
    # copy-pasted fron nbviewer.utils
    # makes it possible to make nbviewer an optional dependency for clonenotebooks.cloners
    # which is helpful for setups where renderers and cloners are installed in different locations

    # get_encoding_from_headers from requests.utils (1.2.3)
    # (c) 2013 Kenneth Reitz
    # used under Apache 2.0

    def get_encoding_from_headers(headers):
        """Returns encodings from given HTTP Header Dict.
        :param headers: dictionary to extract encoding from.
        """

        content_type = headers.get("content-type")

        if not content_type:
            return None

        content_type, params = cgi.parse_header(content_type)

        if "charset" in params:
            return params["charset"].strip("'\"")

        # per #507, at least some hosts are providing UTF-8 without declaring it
        # while the former choice of ISO-8859-1 wasn't known to be causing problems
        # in the wild
        if "text" in content_type:
            return "utf-8"

    def response_text(response, encoding=None):
        """mimic requests.text property, but for plain HTTPResponse"""
        encoding = encoding or get_encoding_from_headers(response.headers) or "utf-8"
        return response.body.decode(encoding, "replace")
