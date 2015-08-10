from __future__ import absolute_import, unicode_literals

from pipeline.compressors import CompressorBase


class JSMinCompressor(CompressorBase):
    """
    JS compressor based on the Python library jsmin
    (http://pypi.python.org/pypi/jsmin/).
    """
    def compress_js(self, js):
        from jsmin import jsmin
        return jsmin(js)
