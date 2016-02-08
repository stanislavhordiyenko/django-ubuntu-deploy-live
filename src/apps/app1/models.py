from django.db import models
from django.core.urlresolvers import reverse


class AppMo(models.Model):
	slug = models.SlugField(max_length=100, unique=True, db_index=True)
	name = models.CharField(max_length=100)
	description = models.TextField()

	def get_url(self):
		return reverse('app1:view', args=[self.slug, ])

	def __str__(self):
		return "%s" % self.name