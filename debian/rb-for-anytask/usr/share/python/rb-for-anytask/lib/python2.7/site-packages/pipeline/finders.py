from itertools import chain

from django.contrib.staticfiles.finders import BaseFinder, AppDirectoriesFinder, FileSystemFinder, find
from django.utils._os import safe_join

from pipeline.conf import settings


class PipelineFinder(BaseFinder):
    def find(self, path, all=False):
        """
        Looks for files in PIPELINE_CSS and PIPELINE_JS
        """
        matches = []
        for elem in chain(settings.PIPELINE_CSS.values(), settings.PIPELINE_JS.values()):
            if elem['output_filename'] == path:
                match = safe_join(settings.PIPELINE_ROOT, path)
                if not all:
                    return match
                matches.append(match)
        return matches

    def list(self, *args):
        return []


class CachedFileFinder(BaseFinder):
    def find(self, path, all=False):
        """
        Work out the uncached name of the file and look that up instead
        """
        try:
            start, _, extn = path.rsplit('.', 2)
            path = '.'.join((start, extn))
            return find(path, all=all)
        except ValueError:
            return []

    def list(self, *args):
        return []


class PatternFilterMixin(object):
    ignore_patterns = []

    def get_ignored_patterns(self):
        return list(set(self.ignore_patterns))

    def list(self, ignore_patterns):
        if ignore_patterns:
            ignore_patterns = ignore_patterns + self.get_ignored_patterns()
        return super(PatternFilterMixin, self).list(ignore_patterns)


class AppDirectoriesFinder(PatternFilterMixin, AppDirectoriesFinder):
    """
    Like AppDirectoriesFinder, but doesn't return any additional ignored
    patterns.

    This allows us to concentrate/compress our components without dragging
    the raw versions in via collectstatic.
    """
    ignore_patterns = [
        '*.js',
        '*.css',
        '*.less',
        '*.scss',
        '*.styl',
    ]


class FileSystemFinder(PatternFilterMixin, FileSystemFinder):
    """
    Like FileSystemFinder, but doesn't return any additional ignored patterns

    This allows us to concentrate/compress our components without dragging
    the raw versions in too.
    """
    ignore_patterns = [
        '*.js',
        '*.less',
        '*.scss',
        '*.styl',
        '*.sh',
        '*.html',
        '*.md',
        '*.markdown',
        '*.php',
        '*.txt',
        'README*',
        'LICENSE*',
        '*examples*',
        '*test*',
        '*bin*',
        '*samples*',
        '*docs*',
        '*build*',
        '*demo*',
        'Makefile*',
        'Gemfile*',
    ]
