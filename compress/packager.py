import glob
import os
import urlparse

from compress.conf import settings
from compress.compilers import Compiler
from compress.compressors import Compressor
from compress.signals import css_compressed, js_compressed
from compress.storage import storage
from compress.versioning import Versioning


class Packager(object):
    def __init__(self, force=False, verbose=False):
        self.force = force
        self.verbose = verbose
        self.compressor = Compressor(verbose)
        self.versioning = Versioning(verbose)
        self.compiler = Compiler(verbose)
        self.packages = {
            'css': self.create_packages(settings.COMPRESS_CSS),
            'js': self.create_packages(settings.COMPRESS_JS),
        }

    def package_for(self, kind, package_name):
        try:
            return self.packages[kind][package_name].copy()
        except KeyError:
            raise PackageNotFound(
                "No corresponding package for %s package name : %s" % (
                    kind, package_name
                )
            )

    def individual_url(self, filename):
        return urlparse.urljoin(settings.COMPRESS_URL,
            self.compressor.relative_path(filename)[1:])

    def pack_stylesheets(self, package):
        variant = package.get('variant', None)
        return self.pack(package, self.compressor.compress_css, css_compressed,
            variant=variant)

    def compile(self, paths):
        return self.compiler.compile(paths)

    def pack(self, package, compress, signal, **kwargs):
        if settings.COMPRESS_AUTO or self.force:
            need_update, version = self.versioning.need_update(
                package['output'], package['paths'])
            if need_update or self.force:
                output_filename = self.versioning.output_filename(package['output'],
                    self.versioning.version(package['paths']))
                self.versioning.cleanup(package['output'])
                if self.verbose or self.force:
                    print "Version: %s" % version
                    print "Saving: %s" % self.compressor.relative_path(output_filename)
                paths = self.compile(package['paths'])
                content = compress(paths, **kwargs)
                self.save_file(output_filename, content)
                signal.send(sender=self, package=package, version=version)
        else:
            filename_base, filename = os.path.split(package['output'])
            version = self.versioning.version_from_file(filename_base, filename)
        return self.versioning.output_filename(package['output'], version)

    def pack_javascripts(self, package):
        return self.pack(package, self.compressor.compress_js, js_compressed, templates=package['templates'])

    def pack_templates(self, package):
        return self.compressor.compile_templates(package['templates'])

    def save_file(self, filename, content):
        file = storage.open(filename, mode='wb+')
        file.write(content)
        file.close()

    def create_packages(self, config):
        packages = {}
        if not config:
            return packages
        for name in config:
            packages[name] = {}
            if 'external_urls' in config[name]:
                packages[name]['externals'] = config[name]['external_urls']
                continue
            paths = []
            for path in config[name]['source_filenames']:
                full_path = os.path.join(settings.COMPRESS_ROOT, path)
                for path in glob.glob(full_path):
                    path = os.path.normpath(path).replace(settings.COMPRESS_ROOT, '')
                    if not path in paths:
                        paths.append(path)
            packages[name]['paths'] = [path for path in paths if not path.endswith(settings.COMPRESS_TEMPLATE_EXT)]
            packages[name]['templates'] = [path for path in paths if path.endswith(settings.COMPRESS_TEMPLATE_EXT)]
            packages[name]['output'] = config[name]['output_filename']
            packages[name]['context'] = {}
            if 'extra_context' in config[name]:
                packages[name]['context'] = config[name]['extra_context']
            if 'template_name' in config[name]:
                packages[name]['template'] = config[name]['template_name']
            if 'variant' in config[name]:
                packages[name]['variant'] = config[name]['variant']
        return packages


class PackageNotFound(Exception):
    pass
