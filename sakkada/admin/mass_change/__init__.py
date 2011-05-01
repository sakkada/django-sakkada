from django.contrib import admin
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib.admin import widgets
from django.utils.functional import curry
from django.forms.models import modelform_factory, modelformset_factory, inlineformset_factory
from django.conf import settings
from django import forms

class MassChangeAdmin(admin.ModelAdmin):
    list_editable_mass = None

    class Media:
        js = [
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.min.js',
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
            settings.MEDIA_URL + 'admin/jquery/init.js',
        ]

    def __init__(self, *args, **kwargs):
        super(MassChangeAdmin, self).__init__(*args, **kwargs)
        opts = self.model._meta
        self.change_list_template = [
            'admin/mass_change/%s/%s/change_list.html' % (opts.app_label, opts.object_name.lower()),
            'admin/mass_change/%s/change_list.html' % opts.app_label,
            'admin/mass_change/change_list.html',
            'admin/%s/%s/change_list.html' % (opts.app_label, opts.object_name.lower()),
            'admin/%s/change_list.html' % opts.app_label,
            'admin/change_list.html'
        ]

        list_editable_mass_error = False
        if self.list_editable_mass:
            if self.list_editable:
                for i in self.list_editable_mass:
                    if not (i in self.list_display and i in self.list_editable):
                        list_editable_mass_error = True
                        break
            else:
                list_editable_mass_error = True
            if list_editable_mass_error:
                raise Exception('Mass Change: error defining list_editable_mass param. It must contain only list_editable fields.')

    @method_decorator(csrf_protect)
    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """
        Handle the changelist view, the django view for the model instances change list/actions page.
        + Mass change
        """

        if not self.list_editable_mass:
            return super(MassChangeAdmin, self).changelist_view(request, extra_context, *args, **kwargs)

        # django admin minimal code
        from django.contrib.admin.views.main import ERROR_FLAG
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        actions = self.get_actions(request)
        list_display = list(self.list_display)
        ChangeList = self.get_changelist(request)
        try:
            cl = ChangeList(request, self.model, list_display, self.list_display_links, self.list_filter,
                self.date_hierarchy, self.search_fields, self.list_select_related, self.list_per_page, self.list_editable, self)
        except IncorrectLookupParameters:
            if ERROR_FLAG in request.GET.keys():
                return render_to_response('admin/invalid_setup.html', {'title': _('Database error')})
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        # mass update section
        extra_context = extra_context or {}
        allowed_field_types = (widgets.RelatedFieldWidgetWrapper, forms.widgets.TextInput)

        # tweak mass form
        massform = modelform_factory(self.model, fields=self.list_editable_mass, exclude=None, formfield_callback=curry(self.formfield_for_dbfield, request=request))
        for i in massform.base_fields.keys():
            field = massform.base_fields[i]
            field.required_original = field.required
            if isinstance(field.widget, allowed_field_types):
                if not field.required:
                    massform.base_fields['%s_drop' % i] = forms.BooleanField(required=False)
                else:
                    field.required = False
            else:
                del massform.base_fields[i]

        # request
        form = massform(request.POST, request.FILES, prefix="form-mass-change")
        if (request.method == "POST" and self.list_editable and '_save' in request.POST and form.is_valid()):
            data = form.cleaned_data
            save_data = {}
            keys = [i for i in data.keys() if i[-5:] != '_drop']
            for i in keys:
                if data[i] or (data.has_key('%s_drop' % i) and data['%s_drop' % i]):
                    save_data[i] = data[i] if data[i] else None

            select_across   = int(request.POST.get('select_across', 0)) == 1
            selected        = request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME)
            if len(save_data) and (selected or select_across):
                queryset = cl.query_set if select_across else cl.query_set.filter(pk__in=selected)
                queryset.update(**save_data)
                self.message_user(request, "Mass update operation successfull complete. Updated %s items." % queryset.count())
                return HttpResponseRedirect(request.get_full_path())

        tr_mass_form = []
        for i in cl.list_display:
            tr_mass_form.append({'field': form[i], 'field_drop': form['%s_drop' % i] if form.base_fields.has_key('%s_drop' % i) else None} if form.base_fields.has_key(i) else None)
        extra_context = {'mass_change': {'tr_form': tr_mass_form,}}
        return super(MassChangeAdmin, self).changelist_view(request, extra_context, *args, **kwargs)