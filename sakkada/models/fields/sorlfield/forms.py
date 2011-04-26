from django.forms.fields import ImageField
from widgets import DeleteImageWidget

class DeleteImageFormField(ImageField):
    def __init__(self, *args, **kwargs):
        kwargs["widget"] = DeleteImageWidget(show_delete_checkbox=not kwargs.get("required", True),
                                             thumbnail=kwargs.pop("thumbnail", None), 
                                             thumbnail_tag=kwargs.pop("thumbnail_tag", None),)
        super(DeleteImageFormField, self).__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        return '__deleted__' if data == '__deleted__' else super(DeleteImageFormField, self).clean(data, initial)