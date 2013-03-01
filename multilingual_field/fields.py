from collections import Mapping
from flask import current_app
from flask.ext.babel import get_locale
from mongoengine.base import ComplexBaseField


def get_language(default='de'):
    try:
        default = current_app.config['BABEL_DEFAULT_LOCALE']
    except:
        pass

    return get_locale() and get_locale().language or default


def rotate_locales(translations, language):

    try:
        languages = current_app.config['ACCEPT_LANGUAGES']
    except:
        languages = ['de', 'en', 'ru']

    rotation = languages.insert(0, language)

    trans = [translations.get(lang) for lang in rotation]
    return len(trans) and trans[0] or u''


class LocaleDict(dict):

    def __new__(cls, data=None):
        self = dict.__new__(cls)

        if data:

            if not isinstance(data, Mapping):
                raise ValueError(
                    'Initial data must be instance of any mapping')

            for k, v in data.items():
                self[k] = unicode(v)

        return self

    def __init__(self, *args, **kwargs):
        pass

    def __getitem__(self, key):
        return super(LocaleDict, self).__getitem__(key)

    def __setitem__(self, key, value):
        return super(LocaleDict, self).__setitem__(key, unicode(value))


class MultilingualString(unicode):

    def __new__(cls, translations=None, language='de'):
        translations = LocaleDict(translations)
        value = rotate_locales(translations, language)
        self = unicode.__new__(cls, value)
        self.language = language
        self.translations = translations
        return self

    def translate(self, language):
        return self.__class__(self.translations, language)


def _translate(self, language):

    for field_name, field in self._fields.items():

        if isinstance(field, MultilingualStringField):
            value = getattr(self, field_name)
            setattr(self, field_name, value.translate(language))


class MultilingualStringField(ComplexBaseField):

    def to_mongo(self, value):
        if not isinstance(value, MultilingualString):
            return value
        return [{'lang': k, 'value': v} for k, v in value.translations.items()]

    def to_python(self, value):
        return MultilingualString(
            {item['lang']: item['value'] for item in value})

    def __set__(self, instance, value):

        if not isinstance(value, MultilingualString):

            if isinstance(value, Mapping):
                value = MultilingualString(value)
            elif isinstance(value, basestring):
                old_value = instance._data.get(self.db_field)
                if old_value is None:
                    language = get_language()
                    value = MultilingualString({language: value})
                else:
                    # @todo: improve MultilingualString to handle updates
                    old_value.translations[old_value.language] = value
                    value = old_value.translate(old_value.language)
        super(MultilingualStringField, self).__set__(instance, value)

    def __get__(self, instance, owner):

        if not hasattr(instance, 'translate'):
            owner.translate = _translate

        return (
            super(MultilingualStringField, self).__get__(instance, owner) or
            MultilingualString())

    def lookup_member(self, member_name):
        return member_name != 'S' and member_name or None
