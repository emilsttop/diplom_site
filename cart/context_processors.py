def cart_count(request):
    """Возвращает количество товаров в корзине для отображения в шапке"""
    cart = request.session.get('cart', {})
    count = 0
    for key, item in cart.items():
        if isinstance(item, dict) and 'total_price' in item:
            # Новый формат: пакет с услугами
            count += 1  # Каждый пакет считается как один товар
        elif isinstance(item, int):
            # Старый формат: просто ID услуги с количеством
            count += item
        else:
            # Если что-то другое — считаем как 1
            count += 1
    return {'cart_count': count}