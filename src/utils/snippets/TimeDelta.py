import datetime
import re

from django.db import models
from django import forms
from django.db.backends.mysql.base import django_conversions
from django.conf import settings
from MySQLdb.constants import FIELD_TYPE

from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy as __
from django.utils.translation import npgettext_lazy as ___

SECONDS_PER_MIN = 60
SECONDS_PER_HOUR = SECONDS_PER_MIN * 60
SECONDS_PER_DAY = SECONDS_PER_HOUR * 24

#south migration patch
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^util\.snippets\.TimeDelta\.TimeDeltaField"])
except ImportError:
    pass
#end of south migration patch

class timedelta(datetime.timedelta):
    def __unicode__(self):
        return timedeltatostr(self)
    def __str__(self):
        return timedeltatostr(self).encode('utf-8')

TIMEDELTASPLIT = re.compile('^(-)?(([0-9]+)[^0-9:]+)?(([0-9]+)(:(([0-9]+)(:([0-9]+))?))?)?$')

def strtotimedelta(s):
    if s is None:
        return None
    m = TIMEDELTASPLIT.match(s)
    if not m:
        return None
    dd,hh,mm,ss = [ int(v) if v and v.isdigit() else 0 for v in m.group(3,5,8,10)]
    sign = -1 if m.group(1) else 1
    return timedelta(days=dd,seconds=ss+(60*(mm+(60*hh))))*sign

def timedeltatostr(v):
    if v is None:
        return None
    if not v:
        return ''
    sign = ''
    if v < timedelta(0):
        v = -v
        sign = '-'
    dd,hh,mm,ss = v.days,int(v.seconds / SECONDS_PER_HOUR),int( (v.seconds % SECONDS_PER_HOUR) / SECONDS_PER_MIN),v.seconds % SECONDS_PER_MIN
    if dd:
        return u'%s%s %02i:%02i:%02i' % (sign,unicode(__("%02d day","%02d days",dd)) % dd,hh,mm,ss)
    return u'%s%02i:%02i:%02i' % (sign,hh,mm,ss)
    #return '%02i:%02i:%02i' % (hh+dd*24,mm,ss)

class TimeDeltaField(models.Field):
    """
    Custom field for mapping TIME columns to timedelta values, not times,
    so that we can store values greater than 24 hours.
    See ticket #354 and http://docs.djangoproject.com/en/1.0/howto/custom-model-fields/#howto-custom-model-fields
    """
    __metaclass__ = models.SubfieldBase
    
    def get_internal_type(self):
        return 'IntegerField'

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, datetime.timedelta):
            return value

        if isinstance(value, basestring):
            return strtotimedelta(value)

        return timedelta(0,value)

    def get_db_prep_value(self, value, connection=None, prepared=None):
        if (value is None) or isinstance(value, (int, long)):
            return value
        total_seconds = value.seconds + (value.days * SECONDS_PER_DAY)
        return total_seconds
        #return '%02i:%02i:%02i' % (
        #    total_seconds / SECONDS_PER_HOUR, # hours
        #    total_seconds / SECONDS_PER_MIN - total_seconds / SECONDS_PER_HOUR * 60, # minutes - Total seconds subtract the used hours
        #    total_seconds % SECONDS_PER_MIN # seconds
        #)

    def formfield(self, *args, **kwargs):
        defaults={'form_class': TimeDeltaFormField}
        defaults.update(kwargs)
        return super(TimeDeltaField, self).formfield(*args, **defaults)

class TimeDeltaFormField(forms.Field):
    default_error_messages = {
        'invalid':  _(u'Enter [days ][hours[:minutes[:seconds]]]'),
        }

    def __init__(self, *args, **kwargs):
        defaults={'widget': TimeDeltaWidget}
        defaults.update(kwargs)
        super(TimeDeltaFormField, self).__init__(*args, **defaults)

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, datetime.timedelta):
            return value

        if isinstance(value, basestring):
            return strtotimedelta(value)

        return timedelta(0,value)

    def clean(self, value):
        #r = super(TimeDeltaFormField, self).clean(value)
        r = strtotimedelta(value)
        if r is None and not (value is None):
            raise forms.ValidationError(self.error_messages['invalid'])
        return r

class TimeDeltaWidget(forms.TextInput):
    def __init__(self, attrs=None):
        super(TimeDeltaWidget, self).__init__(attrs)

    def _format_value(self, value):
        if isinstance(value,datetime.timedelta):
            return str(value)
        if isinstance(value,basestring):
            v = strtotimedelta(value)
            if v:
                return str(v)
            return value
        return value

    def _has_changed(self, initial, data):
        # If our field has show_hidden_initial=True, initial will be a string
        # formatted by HiddenInput using formats.localize_input, which is not
        # necessarily the format used for this  widget. Attempt to convert it.
        try:
            initial = strtotimedelta(initial)
        except (TypeError, ValueError):
            pass
        return super(TimeDeltaWidget, self)._has_changed(self._format_value(initial), data)
