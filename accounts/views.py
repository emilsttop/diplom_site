from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm
from orders.models import Order
from users.models import User

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('catalog')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('catalog')
        else:
            return render(request, 'accounts/login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'accounts/login.html')

def user_logout(request):
    logout(request)
    return redirect('catalog')

@login_required
def profile(request):
    # Если пользователь менеджер или админ — отправляем в его панель
    if request.user.role in ['manager', 'admin']:
        return redirect('manager_dashboard')
    
    # Для клиента показываем личный кабинет
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'accounts/profile.html', {'orders': orders})

@login_required
def specialist_dashboard(request):
    if request.user.role not in ['programmer', 'marketer', 'smm']:
        return redirect('catalog')
    
    role_field = f'{request.user.role}_hours'
    orders = Order.objects.filter(**{f'{role_field}__gt': 0}).order_by('-created_at')
    
    total_hours = sum(getattr(order, role_field, 0) for order in orders)
    
    role_display = {
        'programmer': 'Программист',
        'marketer': 'Маркетолог',
        'smm': 'SMM-менеджер',
    }.get(request.user.role, request.user.role)
    
    return render(request, 'accounts/specialist_dashboard.html', {
        'orders': orders,
        'role': request.user.role,
        'role_field': role_field,           # ← ДОБАВИТЬ
        'role_display': role_display,
        'total_hours': total_hours,
    })