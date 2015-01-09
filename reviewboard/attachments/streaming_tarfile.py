from __future__ import unicode_literals

import tarfile
import time
from io import BytesIO


class FileStream(object):
    """File stream for streaming reponses (review request attachments)

    This buffer intended for use as an argument to StreamingHTTPResponse
    and also as a file for TarFile to write into.

    Files are read in by chunks and written to this buffer through TarFile.
    When there is content to be read from the buffer, it is taken up by
    StreamingHTTPResponse and the buffer is cleared to prevent storing large
    chunks of data in memory.
    """
    def __init__(self):
        self.buffer = BytesIO()
        self.offset = 0

    def write(self, s):
        """Write ``s`` to the buffer and adjust the offset."""
        self.buffer.write(s)
        self.offset += len(s)

    def tell(self):
        """Return the current position of the buffer."""
        return self.offset

    def close(self):
        """Close the buffer."""
        self.buffer.close()

    def pop(self):
        """Return the current contents of the buffer then clear it."""
        s = self.buffer.getvalue()
        self.buffer.close()

        self.buffer = BytesIO()

        return s


class StreamingTarFile(object):
    """A streaming TarFile object for StreamingHTTPReponse.

    Handles building TarInfo objects for each file and also writing chunks of
    files out to a file object (FileStream).
    """
    MODE = 0644
    BLOCK_SIZE = 4096

    def __init__(self, out_filename, files):
        self.out_filename = out_filename
        self.files = files

    def build_tar_info(self, f):
        """Build a TarInfo object representing one file in a tarball."""
        tar_info = tarfile.TarInfo(f.filename)
        tar_info.mode = self.MODE
        tar_info.size = f.file.size

        try:
            modified_time = f.file.storage.modified_time(f.file.name)
        except NotImplementedError:
            pass

        try:
            tar_info.mtime = time.mktime(modified_time.timetuple())
        except NotImplementedError:
            pass

        return tar_info

    def stream_build_tar(self, streaming_fp):
        """Build tarball by writing it's contents out to streaming_fp."""
        tar = tarfile.TarFile.open(self.out_filename, 'w|gz', streaming_fp)

        for f in self.files:
            tar_info = self.build_tar_info(f)
            tar.addfile(tar_info)

            yield

            while True:
                s = f.file.read(self.BLOCK_SIZE)

                if len(s) > 0:
                    tar.fileobj.write(s)
                    yield

                if len(s) < self.BLOCK_SIZE:
                    blocks, remainder = divmod(tar_info.size,
                                               tarfile.BLOCKSIZE)

                    if remainder > 0:
                        tar.fileobj.write(tarfile.NUL *
                                          (tarfile.BLOCKSIZE - remainder))

                        yield

                        blocks += 1

                    tar.offset += blocks * tarfile.BLOCKSIZE
                    break

        yield
        tar.close()

    def generate(self):
        """Generates the tarball containing the file, in chunks.

        This will build the contents of the tarball, yielding chunks as they're
        generated.
        """
        streaming_fp = FileStream()

        for i in self.stream_build_tar(streaming_fp):
            s = streaming_fp.pop()

            if len(s) > 0:
                yield s
