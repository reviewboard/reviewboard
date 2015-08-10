from django.conf import settings


class EvolutionOperationsMulti(object):
    def __init__(self, db_name, database_sig=None):
        database_sig = database_sig or {}

        try:
            from django.db import connections
            engine = settings.DATABASES[db_name]['ENGINE'].split('.')[-1]
            connection = connections[db_name]
            module_name = ['django_evolution.db', engine]
            module = __import__('.'.join(module_name), {}, {}, [''])
            self.evolver = module.EvolutionOperations(database_sig, connection)
        except ImportError:
            if hasattr(settings, 'DATABASE_ENGINE'):
                module_name = ['django_evolution.db', settings.DATABASE_ENGINE]
                module = __import__('.'.join(module_name), {}, {}, [''])
                self.evolver = module.EvolutionOperations(database_sig)
            else:
                raise

    def get_evolver(self):
        return self.evolver
