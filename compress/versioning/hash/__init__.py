import cStringIO
from hashlib import md5, sha1

from compress.conf import settings
from compress.storage import storage
from compress.versioning import VersioningBase


class HashVersioningBase(VersioningBase):
    def __init__(self, hash_method):
        self.hash_method = hash_method

    def need_update(self, output_file, paths, version):
        output_file_name = self.output_filename(output_file, version)
        placeholder = settings.COMPRESS_VERSION_PLACEHOLDER
        try:
            placeholder_index = output_file.index(placeholder)
            old_version = output_file_name[placeholder_index:placeholder_index + len(placeholder) - len(output_file)]
            return (version != old_version), version
        except ValueError:
            # no placeholder found, do not update, manual update if needed
            return False, version

    def concatenate(self, paths):
        """Concatenate together a list of files"""
        return '\n'.join([self.read_file(path) for path in paths])

    def read_file(self, path):
        """Read file content in binary mode"""
        file = storage.open(path, 'rb')
        content = file.read()
        file.close()
        return content

    def version(self, paths):
        buf = self.concatenate(paths)
        s = cStringIO.StringIO(buf)
        version = self.get_hash(s)
        s.close()
        return version

    def get_hash(self, f, CHUNK=2 ** 16):
        m = self.hash_method()
        while 1:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            m.update(chunk)
        return m.hexdigest()


class MD5Versioning(HashVersioningBase):
    def __init__(self):
        super(MD5Versioning, self).__init__(md5)


class SHA1Versioning(HashVersioningBase):
    def __init__(self):
        super(SHA1Versioning, self).__init__(sha1)
