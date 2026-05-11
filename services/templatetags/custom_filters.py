from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Разделяет строку по разделителю"""
    return value.split(arg)

@register.filter
def strip(value):
    """Удаляет пробелы в начале и конце строки"""
    return value.strip()