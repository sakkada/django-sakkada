from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.utils import model_ngettext
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _, gettext_lazy
from .utils import get_copied_objects


# original - django.contrib.admin.actions.delete_selected (v2.1.0)
def copy_selected(modeladmin, request, queryset):
    """
    Action which copies the selected objects.

    This action first displays a confirmation page which shows all the
    creatable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it copies all selected objects and redirects back to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Populate creatable_objects, a data structure of all related objects that
    # will also be created.
    creatable_objects, model_count, perms_needed, collector = get_copied_objects(
        queryset, request, modeladmin.admin_site,
        handlers=getattr(modeladmin, 'copy_selected_handlers', None)
    )

    # The user has already confirmed the deletion.
    # Do the creation and return None to display the change list view again.
    if request.POST.get('post'):
        if perms_needed:
            raise PermissionDenied
        n = queryset.count()
        if n:
            for obj in queryset:
                change_message = modeladmin.construct_change_message(
                    request, None, None, True)
                modeladmin.log_addition(request, obj, change_message)
            # copy all objects with related objects
            collector.copy()
            modeladmin.message_user(
                request, _("Successfully created %(count)d %(items)s.") % {
                    "count": n, "items": model_ngettext(modeladmin.opts, n)
                }, messages.SUCCESS)
        # Return None to display the change list page again.
        return None

    objects_name = model_ngettext(queryset)

    if perms_needed:
        title = _("Cannot create %(name)s") % {"name": objects_name,}
    else:
        title = _("Are you sure?")

    context = {
        **modeladmin.admin_site.each_context(request),
        'title': title,
        'objects_name': str(objects_name),
        'creatable_objects': [creatable_objects],
        'model_count': dict(model_count).items(),
        'queryset': queryset,
        'perms_lacking': perms_needed,
        'opts': opts,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'media': modeladmin.media,
    }

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(
        request,
        getattr(modeladmin, 'copy_selected_confirmation_template', None) or [
            "admin/%s/%s/copy_selected_confirmation.html" % (app_label, opts.model_name),
            "admin/%s/copy_selected_confirmation.html" % app_label,
            "admin/copy_selected_confirmation.html"
        ],
        context
    )


copy_selected.allowed_permissions = ('add',)
copy_selected.short_description = gettext_lazy('Copy selected %(verbose_name_plural)s')
