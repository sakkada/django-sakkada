# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import Media


class MarkListAdmin(admin.ModelAdmin):
    """
    Marks List ModelAdmin Mixin.

    Available keys for "marks_config" (list of dicts) are:
      on        - css color in active state (required),
      off       - css color in inactive state (required),
      condition - obj.attr name to check or callable(obj) (required),
      title     - title of mark element (required),
      row_on    - if defined and mark is active, css background-color
                  of line (table.tr), containing this mark (optional),
      row_off   - if defined and mark is inactive, css background-color
                  of line (table.tr), containing this mark (optional),
      weight    - if several marks active+row_on or inactive+row_off
                  at the same time, most heavy weighted will be chosen,
                  firstly looks for active+row_on marks, if no one,
                  secondary look for inactive+row_off
                  (optional, default is 500).
    """
    marks_config = None

    @property
    def media(self):
        js = '' if settings.DEBUG else '.min'
        js = (
            'admin/js/vendor/jquery/jquery%s.js' % js,
            'admin/js/jquery.init.js',
            'admin/mark_list/scripts.js',
        )
        base = getattr(super(MarkListAdmin, self), 'media', Media())
        return base + Media(js=js)

    def marks(self, obj):
        if not self.marks_config:
            return u''

        links = []
        for m in self.marks_config:
            condition = (m['condition'](obj) if callable(m['condition']) else
                         getattr(obj, m['condition'], False))
            attrs = {
                'data-on': m['on'],
                'data-row-on': m.get('row_on', None),
                'data-row-off': m.get('row_off', None),
                'data-weight': m.get('weight', 500),
                'data-active': 'yes' if condition else None,
            }

            links.append(
                '<span %s style="color: %s; cursor: pointer;" title="%s">'
                '&#11044;</span>'
                % (' '.join(['%s="%s"' % i for i in attrs.items() if i[1]]),
                   m['on'] if condition else m['off'], m['title'],)
            )

        return ''.join([
            '<span class="marks">',
            '<span class="marks-bar"><nobr>', ''.join(links), '</nobr></span>',
            '<pre style="display: none;">%s</pre>' % self.marks_info(obj),
            '</span>'
        ])
    marks.allow_tags = True
    marks.short_description = _('Marks')

    def marks_info(self, obj):
        """Generated preformatted information string"""
        info = [(m['title'], (m['condition'](obj)
                              if callable(m['condition']) else
                              getattr(obj, m['condition'], False)),)
                for m in self.marks_config]
        return '\n'.join(['{} - {}'.format(int(bool(v)), k)
                          for k, v in info])
