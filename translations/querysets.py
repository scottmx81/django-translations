"""This module contains the querysets for the Translations app."""

from django.db.models import query

from translations.utils import _get_standard_language
from translations.query import _fetch_translations_query_getter
from translations.context import Context


__docformat__ = 'restructuredtext'


class TranslatableQuerySet(query.QuerySet):
    """A queryset which provides custom translation functionalities."""

    def __init__(self, *args, **kwargs):
        """Initialize the queryset."""
        super(TranslatableQuerySet, self).__init__(*args, **kwargs)
        self._trans_lang = None
        self._trans_rels = ()
        self._trans_cipher = True
        self._trans_cache = False

    def _chain(self, **kwargs):
        """Return a copy of the current queryset."""
        clone = super(TranslatableQuerySet, self)._chain(**kwargs)

        # default values for all
        clone._trans_lang = getattr(self, '_trans_lang')
        clone._trans_rels = getattr(self, '_trans_rels')
        clone._trans_cipher = getattr(self, '_trans_cipher')

        # reset cache on chaining
        clone._trans_cache = False

        return clone

    def _translate_mode(self):
        """Return whether the queryset is in translate mode."""
        return self._trans_lang is not None and self._trans_cipher

    def _fetch_all(self):
        """Evaluate the queryset."""
        super(TranslatableQuerySet, self)._fetch_all()

        if not self._translate_mode():
            return

        if self._iterable_class is not query.ModelIterable:
            raise TypeError(
                'Translations does not support custom iteration (yet). ' +
                'e.g. values, values_list, etc. ' +
                'If necessary you can `decipher` and then do it.'
            )

        if not self._trans_cache:
            with Context(self._result_cache, *self._trans_rels) \
                    as context:
                context.read(self._trans_lang)
            self._trans_cache = True

    def apply(self, lang=None):
        """Apply a language on the queryset."""
        clone = self.all()
        clone._trans_lang = _get_standard_language(lang)
        return clone

    def translate_related(self, *fields):
        """Translate some relations of the queryset."""
        clone = self.all()
        clone._trans_rels = () if fields == (None,) else fields
        return clone

    def cipher(self):
        """Use the applied language in the queryset."""
        clone = self.all()
        clone._trans_cipher = True
        return clone

    def decipher(self):
        """Use the default language in the queryset."""
        clone = self.all()
        clone._trans_cipher = False
        return clone

    def filter(self, *args, **kwargs):
        """Filter the queryset with lookups and queries."""
        if self._translate_mode():
            query = _fetch_translations_query_getter(self.model, self._trans_lang)(*args, **kwargs)
            return super(TranslatableQuerySet, self).filter(query)
        else:
            return super(TranslatableQuerySet, self).filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        """Exclude the queryset with lookups and queries."""
        if self._translate_mode():
            query = _fetch_translations_query_getter(self.model, self._trans_lang)(*args, **kwargs)
            return super(TranslatableQuerySet, self).exclude(query)
        else:
            return super(TranslatableQuerySet, self).exclude(*args, **kwargs)
