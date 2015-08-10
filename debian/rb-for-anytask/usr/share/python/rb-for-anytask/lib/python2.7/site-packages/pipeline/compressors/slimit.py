from __future__ import absolute_import, unicode_literals

from pipeline.compressors import CompressorBase


class SlimItCompressor(CompressorBase):
    """
    JS compressor based on the Python library slimit
    (http://pypi.python.org/pypi/slimit/).
    """
    def compress_js(self, js):
        from slimit import minify
        return minify(js)
