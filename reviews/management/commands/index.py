from datetime import datetime
import os
import optparse
import sys
import time

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.db.models import Q

from reviews.models import ReviewRequest

try:
    import lucene
    lucene.initVM(lucene.CLASSPATH)
    have_lucene = True
except ImportError:
    # This is here just in case someone is misconfigured but manages to
    # skip the dependency checks inside manage.py (perhaps they have
    # DEBUG = False)
    have_lucene = False


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        optparse.make_option('--full', action='store_false',
                             dest='incremental', default=True,
                             help='Do a full (level-0) index of the database'),
        )
    help = "Creates a search index of review requests"
    requires_model_validation = True

    def handle_noargs(self, **options):
        # Refuse to do anything if they haven't turned on search.
        if not settings.ENABLE_SEARCH:
            sys.stderr.write('ENABLE_SEARCH is set to False in '
                             'settings_local.py.  This needs to be set to '
                             'True to run this command.\n')
            sys.exit(1)

        if not have_lucene:
            sys.stderr.write('PyLucene is required to build the search index.\n')
            sys.exit(1)

        incremental = options.get('incremental', True)

        store_dir = settings.SEARCH_INDEX
        if not os.path.exists(store_dir):
            os.mkdir(store_dir)
        timestamp_file = os.path.join(store_dir, 'timestamp')

        timestamp = 0
        if incremental:
            try:
                f = open(timestamp_file, 'r')
                timestamp = datetime.fromtimestamp(int(f.read()))
                f.close()
            except IOError:
                incremental = False

        f = open(timestamp_file, 'w')
        f.write('%d' % time.time())
        f.close()

        store = lucene.FSDirectory.getDirectory(store_dir, False)
        writer = lucene.IndexWriter(store, False,
                                    lucene.StandardAnalyzer(),
                                    not incremental)

        status = Q(status='P') | Q(status='S')
        objects = ReviewRequest.objects.filter(status)
        if incremental:
            query = Q(last_updated__gt=timestamp)
            # FIXME: re-index based on reviews once reviews are indexed.  I
            # tried ORing this in, but it doesn't seem to work.
            #        Q(review__timestamp__gt=timestamp)
            objects = objects.filter(query)

        if sys.stdout.isatty():
            print 'Creating Review Request Index'
        totalobjs = objects.count()
        i = 0
        prev_pct = -1

        for request in objects:
            try:
                # Remove the old documents from the index
                if incremental:
                    writer.deleteDocuments(lucene.Term('id', str(request.id)))

                self.index_review_request(writer, request)

                if sys.stdout.isatty():
                    i += 1
                    pct = (i * 100 / totalobjs)
                    if pct != prev_pct:
                        sys.stdout.write("  [%s%%]\r" % pct)
                        sys.stdout.flush()
                        prev_pct = pct

            except Exception, e:
                sys.stderr.write('Error indexing ReviewRequest #%d: %s\n' % \
                                 (request.id, e))

        if sys.stdout.isatty():
            print 'Optimizing Index'
        writer.optimize()

        if sys.stdout.isatty():
            print 'Indexed %d documents' % totalobjs
            print 'Done'

        writer.close()

    def index_review_request(self, writer, request):
        # There are several fields we want to make available to users.
        # We index them individually, but also create a big hunk of text
        # to use for the default field, so people can just type in a
        # string and get results.
        doc = lucene.Document()
        doc.add(lucene.Field('id', str(request.id),
                             lucene.Field.Store.YES,
                             lucene.Field.Index.NO))
        doc.add(lucene.Field('summary', request.summary,
                             lucene.Field.Store.NO,
                             lucene.Field.Index.TOKENIZED))
        # Remove commas, since lucene won't tokenize it right with them
        bugs = ' '.join(request.bugs_closed.split(','))
        doc.add(lucene.Field('bug', bugs,
                             lucene.Field.Store.NO,
                             lucene.Field.Index.TOKENIZED))

        name = ' '.join([request.submitter.username,
                         request.submitter.get_full_name()])
        doc.add(lucene.Field('author', name,
                             lucene.Field.Store.NO,
                             lucene.Field.Index.TOKENIZED))
        doc.add(lucene.Field('username', request.submitter.username,
                             lucene.Field.Store.NO,
                             lucene.Field.Index.UN_TOKENIZED))

        # FIXME: index reviews
        # FIXME: index dates

        files = []
        if request.diffset_history:
            for diffset in request.diffset_history.diffsets.all():
                for filediff in diffset.files.all():
                    if filediff.source_file:
                        files.append(filediff.source_file)
                    if filediff.dest_file:
                        files.append(filediff.dest_file)
        aggregate_files = '\n'.join(set(files))
        # FIXME: this tokenization doesn't let people search for files
        # in a really natural way.  It'll split on '/' which handles the
        # majority case, but it'd be nice to be able to drill down
        # (main.cc, vmuiLinux/main.cc, and player/linux/main.cc)
        doc.add(lucene.Field('file', aggregate_files,
                             lucene.Field.Store.NO,
                             lucene.Field.Index.TOKENIZED))

        text = '\n'.join([request.summary,
                          request.description,
                          request.testing_done,
                          bugs,
                          name,
                          aggregate_files])
        doc.add(lucene.Field('text', text,
                             lucene.Field.Store.NO,
                             lucene.Field.Index.TOKENIZED))
        writer.addDocument(doc)
