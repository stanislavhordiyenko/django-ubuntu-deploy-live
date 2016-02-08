{% for appmo in appmos %}
	<a href="{{ appmo.get_url }}">{{ appmo.name }}</a><br />
{% endfor %}