from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import Media
from django.utils.safestring import mark_safe


class MarkListAdmin(admin.ModelAdmin):
    """
    Marks List ModelAdmin Mixin.

    Available keys for "marks_config" (list of dicts) are:
      on        - CSS color in active state (required),
      off       - CSS color in inactive state (required),
      condition - get_marks "marks" key or obj.attr name to check (required),
      title     - Title of mark element (required),
      row_on    - If defined and mark is active/inactive and get_marks "color"
      row_off     value is None, css background-color of table.tr will be set
                  from row_on/row_off value (optional),
      weight_on - If several marks colors are defined, they will be sorted by
      weight_off  weight_x value, weight_on if active and vice versa,
                  by default weights of on and off are 500 and 300 (optional)
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
            return ''

        data = self.get_marks(obj)
        marks = data.get('marks', None) or {}
        color = [data.get('color', None)]

        links = []
        for m in self.marks_config:
            condition = bool(marks[m['condition']]
                             if m['condition'] in marks else
                             getattr(obj, m['condition'], False))
            if condition and 'row_on' in m:
                color.append(
                    (m.get('weight_on', 500), condition, m['row_on'],))
            elif not condition and 'row_off' in m:
                color.append(
                    (m.get('weight_off', 300), condition, m['row_off'],))

            attrs = {'data-on': m['on'],}
            attrs = ' '.join(['%s="%s"' % i for i in attrs.items() if i[1]])
            links.append(
                '<span %s style="color: %s; cursor: pointer;" title="%s">'
                '&#11044;</span>'
                % (attrs, m['on'] if condition else m['off'], m['title'],)
            )

        # get tr color (False in get_marks means no color)
        if color[0] is None and len(color) > 1:
            color = sorted(color[1:], reverse=True, key=lambda x: x[:2])[0][2]
        elif color[0] is False:
            color = None
        else:
            color = color[0]

        return mark_safe(
            '<span%s class="marks">'
            '  <span class="marks-bar"><nobr>%s</nobr></span>'
            '  <pre style="display: none;">%s</pre>'
            '</span>' % (
                ' data-row-color="%s"' % color if color else '',
                ''.join(links), self.get_marks_label(obj, data),
            )
        )
    marks.short_description = _('Marks')

    def get_marks(self, obj):
        return {}

    def get_marks_label(self, obj, data):
        """Generated preformatted information string"""
        marks = data.get('marks', None) or {}
        label = data.get('label', None) or {}
        if label:
            info = label.items()
        else:
            info = [(m['title'], (marks[m['condition']]
                                  if m['condition'] in marks else
                                  getattr(obj, m['condition'], False)),)
                    for m in self.marks_config]
        keylen = max(len(i[0]) for i in info) + 2
        return '\n'.join('{:<{len}} {}'.format(*i, len=keylen) for i in info)
