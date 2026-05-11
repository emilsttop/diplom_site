def cart_count(request):
    """Возвращает количество товаров в корзине для отображения в шапке"""
    cart = request.session.get('cart', {})
    count = sum(cart.values())
    return {'cart_count': count}