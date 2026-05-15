from django import template

register = template.Library()

@register.filter
def getattr(obj, attr):
    """Возвращает атрибут объекта по имени"""
    try:
        return getattr(obj, attr, 0)
    except AttributeError:
        return 0