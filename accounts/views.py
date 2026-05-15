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
            print("=== USER REGISTER SUCCESS ===")
            print("Session keys:", request.session.keys())
            print("pending_package_id:", request.session.get('pending_package_id'))
            print("pending_service_ids:", request.session.get('pending_service_ids'))
            
            # Восстанавливаем отложенные услуги
            pending_package_id = request.session.pop('pending_package_id', None)
            pending_service_ids = request.session.pop('pending_service_ids', None)
            
            if pending_package_id and pending_service_ids:
                # Добавляем в корзину
                cart = request.session.get('cart', {})
                package_key = f"package_{pending_package_id}"
                
                # Здесь нужно получить услуги по их ID
                service_ids_list = json.loads(pending_service_ids)
                services = Service.objects.filter(id__in=service_ids_list)
                
                if services.exists():
                    total_price = sum(s.price for s in services)
                    cart[package_key] = {
                        'package_name': ServicePackage.objects.get(id=pending_package_id).name,
                        'service_ids': service_ids_list,
                        'service_names': [s.name for s in services],
                        'services': [{
                            'name': s.name,
                            'price': float(s.price),
                            'programmer_hours': float(s.programmer_hours),
                            'marketer_hours': float(s.marketer_hours),
                            'smm_hours': float(s.smm_hours),
                        } for s in services],
                        'total_price': float(total_price),
                    }
                    request.session['cart'] = cart
            
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
            print("=== USER LOGIN SUCCESS ===")
            print("Session keys:", request.session.keys())
            print("pending_package_id:", request.session.get('pending_package_id'))
            print("pending_service_ids:", request.session.get('pending_service_ids'))
            
            # Восстанавливаем отложенные услуги (если есть)
            pending_package_id = request.session.pop('pending_package_id', None)
            pending_service_ids = request.session.pop('pending_service_ids', None)
            
            if pending_package_id and pending_service_ids:
                import json
                from services.models import Service, ServicePackage
                
                cart = request.session.get('cart', {})
                package_key = f"package_{pending_package_id}"
                
                service_ids_list = json.loads(pending_service_ids)
                services = Service.objects.filter(id__in=service_ids_list)
                
                if services.exists():
                    total_price = sum(s.price for s in services)
                    cart[package_key] = {
                        'package_name': ServicePackage.objects.get(id=pending_package_id).name,
                        'service_ids': service_ids_list,
                        'service_names': [s.name for s in services],
                        'services': [{
                            'name': s.name,
                            'price': float(s.price),
                            'programmer_hours': float(s.programmer_hours),
                            'marketer_hours': float(s.marketer_hours),
                            'smm_hours': float(s.smm_hours),
                        } for s in services],
                        'total_price': float(total_price),
                    }
                    request.session['cart'] = cart
                    print(f"✅ Восстановлена корзина после входа: {cart}")
            
            return redirect('catalog')
        else:
            return render(request, 'accounts/login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'accounts/login.html')

def user_logout(request):
    logout(request)
    return redirect('catalog')

@login_required
def profile(request):
    # Если пользователь менеджер или админ — отправляем в панель менеджера
    if request.user.role in ['manager', 'admin']:
        return redirect('manager_dashboard')
    
    # Если пользователь специалист (программист, маркетолог, SMM) — отправляем в его панель
    if request.user.role in ['programmer', 'marketer', 'smm']:
        return redirect('specialist_dashboard')
    
    # Для клиента показываем личный кабинет
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'accounts/profile.html', {'orders': orders})

@login_required
def specialist_dashboard(request):
    if request.user.role not in ['programmer', 'marketer', 'smm']:
        return redirect('catalog')
    
    role = request.user.role
    role_field = f'{role}_hours'
    
    # Фильтруем заказы по назначенному специалисту, исключая выполненные
    if role == 'programmer':
        orders = Order.objects.filter(assigned_programmer=request.user).exclude(status='completed').order_by('-created_at')
    elif role == 'marketer':
        orders = Order.objects.filter(assigned_marketer=request.user).exclude(status='completed').order_by('-created_at')
    elif role == 'smm':
        orders = Order.objects.filter(assigned_smm=request.user).exclude(status='completed').order_by('-created_at')
    else:
        orders = Order.objects.none()
    
    total_hours = sum(getattr(order, role_field, 0) for order in orders)
    
    role_display = {
        'programmer': 'Программист',
        'marketer': 'Маркетолог',
        'smm': 'SMM-менеджер',
    }.get(role, role)
    
    return render(request, 'accounts/specialist_dashboard.html', {
        'orders': orders,
        'role': role,
        'role_field': role_field,
        'role_display': role_display,
        'total_hours': total_hours,
    })