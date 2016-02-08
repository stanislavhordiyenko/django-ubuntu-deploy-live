from apps.common.decorators import render_to
from django.shortcuts import get_object_or_404

from .models import AppMo


@render_to('app1/list.tpl')
def list(request):
	appmos = AppMo.objects.all()
	return {
		"appmos": appmos,
	}

@render_to('app1/view.tpl')
def view(request, slug):
	appmo = get_object_or_404(AppMo, slug=slug)
	return {
		"appmo": appmo,
	}