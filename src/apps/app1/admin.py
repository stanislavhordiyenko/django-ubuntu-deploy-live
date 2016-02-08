from django.contrib import admin

from .models import AppMo


class AppMoAdmin(admin.ModelAdmin):
	list_display = ('slug', 'name', 'description', )
	fieldsets = (
		(None, {
			'fields': ('slug', )
		}),
		('General Information', {
			'fields': ('name', 'description', )
		}),
	)


admin.site.register(AppMo, AppMoAdmin)