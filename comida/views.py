from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ComidaForm
from .models import Comida


def inicio(request):
    return render(request, 'inicio.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('lista_comidas')

    form = AuthenticationForm(
        request,
        data=request.POST if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        next_url = request.POST.get('next') or request.GET.get('next', '')
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('lista_comidas')

    return render(request, 'login.html', {'form': form})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def lista_comidas(request):
    comidas = Comida.objects.order_by('-id')
    return render(request, 'lista.html', {'comidas': comidas})


@login_required
@require_http_methods(['GET', 'POST'])
def crear_comida(request):
    data = request.POST.copy() if request.method == 'POST' else None
    if data is not None:
        data.setdefault('disponible', 'on')
    form = ComidaForm(data)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('lista_comidas')

    return render(request, 'crear.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def editar_comida(request, id):
    comida = get_object_or_404(Comida, pk=id)
    data = request.POST if request.method == 'POST' else None
    form = ComidaForm(data, instance=comida)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('lista_comidas')

    return render(request, 'editar.html', {'comida': comida, 'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def eliminar_comida(request, id):
    comida = get_object_or_404(Comida, pk=id)
    if request.method == 'POST':
        comida.delete()
        return redirect('lista_comidas')

    return render(request, 'eliminar.html', {'comida': comida})
