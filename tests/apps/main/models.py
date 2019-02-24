from django.db import models
from sakkada.models.prev_next import PrevNextModel


class PrevNextTestModel(PrevNextModel):
    title = models.CharField('title', max_length=128)
    slug = models.SlugField('slug', max_length=128)
    weight = models.IntegerField('weight', default=500)
    nweight = models.IntegerField(
        'weight nullable', default=500, null=True, blank=True)

    class Meta:
        ordering = ('-weight',)

    def __str__(self):
        return '%s (%d: %s)' % (self.title, self.id, self.slug,)
