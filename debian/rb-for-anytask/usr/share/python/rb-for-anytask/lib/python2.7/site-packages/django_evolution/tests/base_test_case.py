import copy
import re

from django.test.testcases import TransactionTestCase

from django_evolution.diff import Diff
from django_evolution.mutators import AppMutator
from django_evolution.signature import create_database_sig
from django_evolution.tests.utils import (create_test_proj_sig,
                                          deregister_models,
                                          execute_test_sql,
                                          register_models_multi,
                                          test_sql_mapping)


class EvolutionTestCase(TransactionTestCase):
    sql_mapping_key = None
    default_database_name = 'default'
    default_model_name = 'TestModel'
    default_base_model = None
    default_pre_extra_models = []
    default_extra_models = []

    ws_re = re.compile(r'\s+')

    def setUp(self):
        self.base_model = None
        self.pre_extra_models = []
        self.extra_models = []
        self.start = None
        self.start_sig = None
        self.database_sig = None
        self.test_database_sig = None

        if self.default_base_model:
            self.set_base_model(self.default_base_model,
                                pre_extra_models=self.default_pre_extra_models,
                                extra_models=self.default_extra_models)

    def tearDown(self):
        deregister_models()

    def shortDescription(self):
        """Returns the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc

    def set_base_model(self, model, name=None, extra_models=[],
                       pre_extra_models=[], db_name=None):
        name = name or self.default_model_name
        db_name = db_name or self.default_database_name

        if self.base_model:
            deregister_models()

        self.base_model = model
        self.pre_extra_models = pre_extra_models
        self.extra_models = extra_models
        self.database_sig = create_database_sig(db_name)

        self.start = self.register_model(model, name,
                                         register_indexes=True,
                                         db_name=db_name)
        self.start_sig = self.create_test_proj_sig(model, name)

    def make_end_signatures(self, model, model_name, db_name=None):
        db_name = db_name or self.default_database_name

        end = self.register_model(model, name=model_name, db_name=db_name)
        end_sig = self.create_test_proj_sig(model, name=model_name)

        return end, end_sig

    def perform_evolution_tests(self, model, evolutions, diff_text=None,
                                expected_hint=None, sql_name=None,
                                model_name=None,
                                end=None, end_sig=None,
                                expect_noop=False,
                                rescan_indexes=True,
                                use_hinted_evolutions=False,
                                perform_simulations=True,
                                perform_mutations=True,
                                db_name=None):
        model_name = model_name or self.default_model_name
        db_name = db_name or self.default_database_name

        if end is None or end_sig is None:
            end, end_sig = self.make_end_signatures(model, model_name, db_name)

        # See if the diff between signatures contains the contents we expect.
        d = self.perform_diff_test(end_sig, diff_text, expected_hint,
                                   expect_empty=expect_noop)

        if use_hinted_evolutions:
            assert not evolutions
            evolutions = d.evolution()['tests']

        if perform_simulations:
            self.perform_simulations(evolutions, end_sig, db_name=db_name)

        if perform_mutations:
            self.perform_mutations(evolutions, end, end_sig, sql_name,
                                   rescan_indexes=rescan_indexes,
                                   db_name=db_name)

    def perform_diff_test(self, end_sig, diff_text, expected_hint,
                          expect_empty=False):
        d = Diff(self.start_sig, end_sig)
        self.assertEqual(d.is_empty(), expect_empty)

        if not expect_empty:
            if diff_text is not None:
                self.assertEqual(str(d), diff_text)

            if expected_hint is not None:
                self.assertEqual(
                    [str(e) for e in d.evolution()['tests']],
                    expected_hint)

        return d

    def perform_simulations(self, evolutions, end_sig, ignore_apps=False,
                            db_name=None):
        db_name = db_name or self.default_database_name

        self.test_database_sig = self.copy_sig(self.database_sig)
        test_sig = self.copy_sig(self.start_sig)

        for mutation in evolutions:
            mutation.simulate('tests', test_sig, self.test_database_sig,
                              database=db_name)

        # Check that the simulation's changes results in an empty diff.
        d = Diff(test_sig, end_sig)
        self.assertTrue(d.is_empty(ignore_apps=ignore_apps))

    def perform_mutations(self, evolutions, end, end_sig, sql_name,
                          rescan_indexes=True, db_name=None):
        def run_mutations():
            app_mutator = AppMutator('tests', test_sig, self.test_database_sig,
                                     db_name)
            app_mutator.run_mutations(evolutions)

            return app_mutator.to_sql()

        db_name = db_name or self.default_database_name

        self.test_database_sig = self.copy_sig(self.database_sig)
        test_sig = self.copy_sig(self.start_sig)

        sql = execute_test_sql(
            self.start, end,
            run_mutations,
            database_sig=self.test_database_sig,
            rescan_indexes=rescan_indexes,
            return_sql=True,
            database=db_name)

        if sql_name is not None:
            print "** Comparing SQL against '%s'" % sql_name
            self.assertEqual('\n'.join(sql),
                             self.get_sql_mapping(sql_name, db_name))

    def get_sql_mapping(self, name, db_name=None):
        db_name = db_name or self.default_database_name

        return test_sql_mapping(self.sql_mapping_key, db_name)[name]

    def register_model(self, model, name, db_name=None, **kwargs):
        db_name = db_name or self.default_database_name

        models = self.pre_extra_models + [(name, model)] + self.extra_models

        return register_models_multi(self.database_sig, 'tests',
                                     db_name, *models, **kwargs)

    def create_test_proj_sig(self, model, name, extra_models=[],
                             pre_extra_models=[]):
        return create_test_proj_sig(*(
            self.pre_extra_models + pre_extra_models + [(name, model)] +
            extra_models + self.extra_models))

    def copy_sig(self, sig):
        return copy.deepcopy(sig)

    def copy_models(self, models):
        return copy.deepcopy(models)
