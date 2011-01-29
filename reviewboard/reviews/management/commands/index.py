from datetime import datetime
import os
import optparse
import sys
import time

from django.core.management.base import NoArgsCommand
from django.db.models import Q

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.reviews.models import ReviewRequest

try:
    import lucene
    lucene.initVM(lucene.CLASSPATH)
    have_lucene = True

    lv = [int(x) for x in lucene.VERSION.split('.')]
    lucene_is_2x = lv[0] == 2 and lv[1] < 9
    lucene_is_3x = lv[0] == 3 or (lv[0] == 2 and lv[1] == 9)
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
        siteconfig = SiteConfiguration.objects.get_current()

        # Refuse to do anything if they haven't turned on search.
        if not siteconfig.get("search_enable"):
            sys.stderr.write('Search is currently disabled. It must be '
                             'enabled in the Review Board administration '
                             'settings to run this command.\n')
            sys.exit(1)

        if not have_lucene:
            sys.stderr.write('PyLucene is required to build the search index.\n')
            sys.exit(1)

        incremental = options.get('incremental', True)

        store_dir = siteconfig.get("search_index_file")
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

        if lucene_is_2x:
            store = lucene.FSDirectory.getDirectory(store_dir, False)
            writer = lucene.IndexWriter(store, False,
                                        lucene.StandardAnalyzer(),
                                        not incremental)
        elif lucene_is_3x:
            store = lucene.FSDirectory.open(lucene.File(store_dir))
            writer = lucene.IndexWriter(store,
                lucene.StandardAnalyzer(lucene.Version.LUCENE_CURRENT),
                not incremental,
                lucene.IndexWriter.MaxFieldLength.LIMITED)
        else:
            assert False

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
        if lucene_is_2x:
            lucene_tokenized = lucene.Field.Index.TOKENIZED
            lucene_un_tokenized = lucene.Field.Index.UN_TOKENIZED
        elif lucene_is_3x:
            lucene_tokenized = lucene.Field.Index.ANALYZED
            lucene_un_tokenized = lucene.Field.Index.NOT_ANALYZED
        else:
            assert False

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
                             lucene_tokenized))
        if request.changenum:
            doc.add(lucene.Field('changenum',
                                 unicode(request.changenum),
                                 lucene.Field.Store.NO,
                                 lucene_tokenized))
        # Remove commas, since lucene won't tokenize it right with them
        bugs = ' '.join(request.bugs_closed.split(','))
        doc.add(lucene.Field('bug', bugs,
                             lucene.Field.Store.NO,
                             lucene_tokenized))

        name = ' '.join([request.submitter.username,
                         request.submitter.get_full_name()])
        doc.add(lucene.Field('author', name,
                             lucene.Field.Store.NO,
                             lucene_tokenized))
        doc.add(lucene.Field('username', request.submitter.username,
                             lucene.Field.Store.NO,
                             lucene_un_tokenized))

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
                             lucene_tokenized))

        text = '\n'.join([request.summary,
                          request.description,
                          unicode(request.changenum),
                          request.testing_done,
                          bugs,
                          name,
                          aggregate_files])
        doc.add(lucene.Field('text', text,
                             lucene.Field.Store.NO,
                             lucene_tokenized))
        writer.addDocument(doc)
