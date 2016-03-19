# -*- coding: utf-8 -*-
# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from zope.component import getGlobalSiteManager
from zope.component import getUtilitiesFor
from zope.schema.vocabulary import VocabularyRegistryError
from zope.schema.vocabulary import getVocabularyRegistry

from i3menu.test import BaseTestCase
from i3menu.vocabs import (
    BaseVocabularyFactory,
    WindowsVocabularyFactory,
    WorkspacesVocabularyFactory,
    OutputsVocabularyFactory,
    init_vocabs,
    VOCABS,
    WindowCommandsVocabularyFactory
)
from i3menu.test import (
    MOCK_WINDOWS_LIST,
    MOCK_WORKSPACES_LIST,
    MOCK_OUTPUTS_LIST
)
from i3menu.interfaces import IWindowCommand

gsm = getGlobalSiteManager()


class TestVocabs(BaseTestCase):

    def test_base_vocabulary_factory(self):
        vocab_factory = BaseVocabularyFactory()
        vocab_factory._terms = [
            ('a', 'a', 'a'),
            ('b', 'b', 'b'),
        ]
        vocab = vocab_factory()
        terms = [t for t in vocab]
        self.assertEqual(len(terms), 2)

    def test_windows_vocabulary_factory(self):
        vocab_factory = WindowsVocabularyFactory()
        vocab = vocab_factory()
        terms = [t for t in vocab]
        self.assertEqual(len(terms), len(MOCK_WINDOWS_LIST))
        self.assertEqual(terms[0].value, MOCK_WINDOWS_LIST[0])

    def test_workspaces_vocabulary_factory(self):
        vocab_factory = WorkspacesVocabularyFactory()
        vocab = vocab_factory()
        terms = [t for t in vocab]
        self.assertEqual(len(terms), len(MOCK_WORKSPACES_LIST))
        self.assertEqual(terms[0].value.workspace, MOCK_WORKSPACES_LIST[0])

    def test_outputs_vocabulary_factory(self):
        vocab_factory = OutputsVocabularyFactory()
        vocab = vocab_factory()
        terms = [t for t in vocab]
        # -1 'cause 1 output is inactive
        self.assertEqual(len(terms), len(MOCK_OUTPUTS_LIST) - 1)
        self.assertEqual(terms[0].value.output, MOCK_OUTPUTS_LIST[0])

    def test_windows_commands_vocabulary_factory(self):
        vf = WindowCommandsVocabularyFactory()
        v = vf()
        terms = [t for t in v]
        cmd_uts = [ut for ut in getUtilitiesFor(IWindowCommand)]
        self.assertEqual(len(terms), len(cmd_uts))

    def test_init_vocabs(self):
        init_vocabs()
        vr = getVocabularyRegistry()
        for v in VOCABS:
            error = False
            try:
                vr.get(self.context, v.name)
            except VocabularyRegistryError as e:
                error = e.message
            self.assertFalse(error, msg=error)