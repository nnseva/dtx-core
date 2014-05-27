#
# -*- coding: utf-8 -*-
#

from mako.lookup import TemplateLookup
import tempfile

from django.conf import settings
from django.template import Context

from django.http import HttpResponse

directories      = getattr(settings, 'MAKO_TEMPLATE_DIRS', settings.TEMPLATE_DIRS)

module_directory = getattr(settings, 'MAKO_MODULE_DIR', None)
if module_directory is None:
    module_directory = tempfile.mkdtemp()

output_encoding  = getattr(settings, 'MAKO_OUTPUT_ENCODING', 'utf-8')
encoding_errors  = getattr(settings, 'MAKO_ENCODING_ERRORS', 'replace')

lookup = TemplateLookup(directories=directories,
                        module_directory=module_directory,
                        output_encoding=output_encoding,
                        encoding_errors=encoding_errors,
                        )


def renderToString(template_name, dictionary, context_instance=None):
    global lookup
    context_instance = context_instance or Context(dictionary)
    context_instance.update(dictionary or {})
    context_dictionary = {}
    for d in context_instance:
        context_dictionary.update(d)
    template = lookup.get_template(template_name)
    return template.render(**context_dictionary)


def renderToResponse(template_name, dictionary, context_instance=None, content_type=None, status=None):
    content = renderToString(template_name, dictionary, context_instance=None)
    return HttpResponse(content, content_type=content_type, status=status)


__all__ = [
    'renderToString',
    'renderToResponse',
]

