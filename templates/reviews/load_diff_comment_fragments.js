{% for entry in comment_entries %}
$("#{{container_prefix}}_{{entry.comment.id}}").html('{{entry.html|escapejs}}');
{% endfor %}

$.funcQueue("{{queue_name}}").next();
