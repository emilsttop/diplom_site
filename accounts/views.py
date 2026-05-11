from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm
from orders.models import Order

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
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'accounts/profile.html', {'orders': orders})