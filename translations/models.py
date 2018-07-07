"""
This module contains the models for the Translations app.

.. rubric:: Classes:

:class:`Translatable`
    An abstract model which can be inherited by any model that needs
    translation capabilities.
:class:`Translation`
    The model which represents the translations.

----
"""

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, \
    GenericRelation
from django.utils.translation import ugettext_lazy as _

from translations.utils import get_translations, translate, update_translations
from translations.managers import TranslatableManager


__docformat__ = 'restructuredtext'


class Translation(models.Model):
    """
    This model represents the translations.

    Each translation belongs to a *unique* database address. Each address is
    composed of a :attr:`content_type` (table), an :attr:`object_id` (row) and
    a :attr:`field` (column).

    Each unique address must have only one translation in a specific
    :attr:`language`.

    .. note::

       :class:`~django.contrib.contenttypes.models.ContentType` is a django
       model which comes with the :mod:`~django.contrib.contenttypes` app.
       This model represents the tables created in the database.

       :attr:`content_type` and :attr:`object_id` together form something
       called a :class:`~django.contrib.contenttypes.fields.GenericForeignKey`.
       This kind of foreign key contrary to the normal foreign key (which can
       point to a row in only one table) can point to a row in any table.
    """

    content_type = models.ForeignKey(
        verbose_name=_('content type'),
        help_text=_('the content type of the object to translate'),
        to=ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.TextField(
        verbose_name=_('object id'),
        help_text=_('the id of the object to translate')
    )
    content_object = GenericForeignKey(
        ct_field='content_type',
        fk_field='object_id'
    )
    field = models.CharField(
        verbose_name=_('field'),
        help_text=_('the field of the object to translate'),
        max_length=64
    )
    language = models.CharField(
        verbose_name=_('language'),
        help_text=_('the language of the translation'),
        max_length=32,
        choices=settings.LANGUAGES
    )
    text = models.TextField(
        verbose_name=_('text'),
        help_text=_('the text of the translation')
    )

    def __str__(self):
        """Return the representation of the translation."""
        return '{source}: {translation}'.format(
            source=getattr(self.content_object, self.field),
            translation=self.text
        )

    class Meta:
        unique_together = ('content_type', 'object_id', 'field', 'language',)
        verbose_name = _('translation')
        verbose_name_plural = _('translations')


class Translatable(models.Model):
    """
    This abstract model can be inherited by any model which needs translation
    capabilities.

    Inheriting this model adds :attr:`translations` relation to the model and
    changes the :attr:`objects` manager of the model to add translation
    capabilities to the ORM.

    .. note::
       There is **no need for migrations** after inheriting this model. Simply
       just use it afterwards!

    .. note::
       The :attr:`translations` relation is a reverse relation to the
       :class:`~django.contrib.contenttypes.fields.GenericForeignKey`
       described in :class:`Translation`.
    """

    objects = TranslatableManager()
    translations = GenericRelation(
        Translation,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name="%(app_label)s_%(class)s"
    )

    class Meta:
        abstract = True

    class TranslatableMeta:
        """This class contains meta information about translation process."""

        fields = None
        """
        :var fields: The fields of the model to be translated, ``None`` means
            use all text based fields automatically, ``[]`` means no fields
            should be translatable.
        :vartype fields: list(str) or None
        """

    @classmethod
    def get_translatable_fields(cls):
        """
        Return the list of translatable fields.

        Return the translatable fields for the model based on
        :attr:`TranslatableMeta.fields`.

        :return: The list of translatable fields
        :rtype: list(~django.db.models.Field)
        """
        if hasattr(cls, 'TranslatableMeta'):
            if cls.TranslatableMeta.fields is None:
                fields = []
                for field in cls._meta.get_fields():
                    if isinstance(
                                field,
                                (models.CharField, models.TextField,)
                            ) and not isinstance(
                                field,
                                models.EmailField
                            ) and not (
                                hasattr(field, 'choices') and field.choices
                            ):
                        fields.append(field)
            else:
                fields = [
                    cls._meta.get_field(field_name)
                    for field_name in cls.TranslatableMeta.fields
                ]
        else:
            raise Exception(
                '{cls} class is not a translatable model.'.format(cls=cls)
            )
        return fields

    def update_translations(self, lang=None):
        """
        Update the translations of the object based on the object properties.

        Use the current properties of the object to update the translations in
        a language.

        :param lang: the language of the translations to update, if ``None``
            is given the current active language will be used.
        :type lang: str or None
        """
        update_translations(self, lang=lang)

    def get_translations(self, *relations, lang=None):
        r"""
        Return the translations of the object and its relations in a language.

        :param \*relations: a list of relations to fetch the translations for.
        :type \*relations: list(str)
        :param lang: the language of the translations to fetch, if ``None``
            is given the current active language will be used.
        :type lang: str or None
        :return: the translations
        :rtype: ~django.db.models.query.QuerySet
        """
        return get_translations(self, *relations, lang=lang)

    def get_translated(self, *relations, lang=None, translations=None):
        r"""
        Return the translated object and its relations in a language.

        Translate the current object and its relations in a language
        based on a queryset of translations and return it. If no
        ``translations`` queryset is given one will be created based on the
        ``relations`` and the ``lang`` parameters.

        .. note::
           It's recommended that the ``translations`` queryset is not passed
           in, so it's calculated automatically. Translations app is pretty
           smart, it will fetch all the translations for the object and its
           relations doing the minimum amount of queries needed (usually one).
           It's only there just in case there is a need to query the
           translations manually.

        :param \*relations: a list of relations to be translated
        :type \*relations: list(str)
        :param lang: the language of the translation, if ``None``
            is given the current active language will be used.
        :type lang: str or None
        :return: the object itself
        :rtype: Translatable
        """
        translate(
            self, *relations,
            lang=lang,
            translations_queryset=translations
        )
        return self