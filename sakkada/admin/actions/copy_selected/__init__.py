# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.utils import model_ngettext
from django.core.exceptions import PermissionDenied
from django.db import router
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _, ugettext_lazy
from .utils import get_copied_objects


def copy_selected(modeladmin, request, queryset):
    """
    Action which copies the selected objects.

    This action first displays a confirmation page whichs shows all the
    creatable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it copies all selected objects and redirects back to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Check that the user has delete permission for the actual model
    if not modeladmin.has_add_permission(request):
        raise PermissionDenied

    using = router.db_for_write(modeladmin.model)

    # Populate creatable_objects, a data structure of all related objects that
    # will also be created.
    creatable_objects, perms_needed, collector = get_copied_objects(
        queryset, opts, request.user, modeladmin.admin_site, using)
    model_count = collector.model_count

    # The user has already confirmed the deletion.
    # Do the deletion and return a None to display the change list view again.
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
            modeladmin.message_user(request, _("Successfully created %(count)d %(items)s.") % {
                "count": n, "items": model_ngettext(modeladmin.opts, n)
            }, messages.SUCCESS)
        # Return None to display the change list page again.
        return None

    if len(queryset) == 1:
        objects_name = force_text(opts.verbose_name)
    else:
        objects_name = force_text(opts.verbose_name_plural)

    if perms_needed:
        title = _("Cannot create %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = dict(
        modeladmin.admin_site.each_context(request),
        title=title,
        objects_name=objects_name,
        creatable_objects=[creatable_objects],
        model_count=dict(model_count).items(),
        queryset=queryset,
        perms_lacking=perms_needed,
        opts=opts,
        action_checkbox_name=helpers.ACTION_CHECKBOX_NAME,
    )

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(request, getattr(modeladmin, 'copy_selected_confirmation_template', None) or [
        "admin/%s/%s/copy_selected_confirmation.html" % (app_label, opts.model_name),
        "admin/%s/copy_selected_confirmation.html" % app_label,
        "admin/copy_selected_confirmation.html"
    ], context)

copy_selected.short_description = ugettext_lazy("Copy selected %(verbose_name_plural)s")
