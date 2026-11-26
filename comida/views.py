from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from functools import wraps
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from datetime import timedelta

from .forms import ComidaForm
from .models import Comida, UserSession


def valid_session_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = f"{reverse('login')}?next={request.path}"
            return redirect(login_url)

        key = request.session.session_key
        if not key:
            logout(request)
            return redirect('login')

        session_record = UserSession.objects.filter(
            user=request.user,
            django_session_key=key,
        ).first()
        if session_record is None:
            session_record = UserSession.objects.create(
                user=request.user,
                django_session_key=key,
                refresh_jti=key,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                expires_at=timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE),
            )
        if session_record.revoked or session_record.expires_at <= timezone.now():
            logout(request)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapped


def inicio(request):
    return render(request, 'inicio.html')


def swagger_ui(request):
    return render(request, 'swagger.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('lista_comidas')

    form = AuthenticationForm(
        request,
        data=request.POST if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        request.session.save()
        UserSession.objects.update_or_create(
            django_session_key=request.session.session_key,
            defaults={
                'user': user,
                'expires_at': timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE),
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
                'revoked': False,
                'refresh_jti': request.session.session_key,
            },
        )
        next_url = request.POST.get('next') or request.GET.get('next', '')
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('lista_comidas')

    return render(request, 'login.html', {'form': form})


@valid_session_required
@require_POST
def logout_view(request):
    UserSession.objects.filter(
        user=request.user,
        django_session_key=request.session.session_key,
    ).update(revoked=True)
    logout(request)
    return redirect('login')


@valid_session_required
def lista_comidas(request):
    comidas = Comida.objects.order_by('-id')
    return render(request, 'lista.html', {'comidas': comidas})


@valid_session_required
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


@valid_session_required
@require_http_methods(['GET', 'POST'])
def editar_comida(request, id):
    comida = get_object_or_404(Comida, pk=id)
    data = request.POST if request.method == 'POST' else None
    form = ComidaForm(data, instance=comida)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('lista_comidas')

    return render(request, 'editar.html', {'comida': comida, 'form': form})


@valid_session_required
@require_http_methods(['GET', 'POST'])
def eliminar_comida(request, id):
    comida = get_object_or_404(Comida, pk=id)
    if request.method == 'POST':
        comida.delete()
        return redirect('lista_comidas')

    return render(request, 'eliminar.html', {'comida': comida})
