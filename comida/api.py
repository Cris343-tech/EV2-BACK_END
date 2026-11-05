import json
import math

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.forms import model_to_dict
from django.http import HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import ComidaForm
from .models import Comida


TOKEN_SALT = 'comida.api-token'
FIELD_ALIASES = {
    'title': 'nombre',
    'nombre': 'nombre',
    'description': 'descripcion',
    'descripcion': 'descripcion',
    'price': 'precio',
    'precio': 'precio',
    'category': 'categoria',
    'categoria': 'categoria',
    'available': 'disponible',
    'disponible': 'disponible',
}
def _json_body(request):
    if request.content_type != 'application/json':
        return None, JsonResponse(
            {'error': 'El Content-Type debe ser application/json.'},
            status=415,
        )

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({'error': 'El JSON no es válido.'}, status=400)

    if not isinstance(payload, dict):
        return None, JsonResponse(
            {'error': 'El cuerpo JSON debe ser un objeto.'},
            status=400,
        )
    return payload, None


def _normalize_payload(payload):
    normalized = {}
    for key, value in payload.items():
        field = FIELD_ALIASES.get(key)
        if field is None:
            return None, {'campo': f'Campo no permitido: {key}.'}
        if field in normalized:
            return None, {'campo': f'El campo {field} está repetido.'}
        if field in {'nombre', 'descripcion', 'categoria'} and not isinstance(value, str):
            return None, {field: 'Debe ser texto.'}
        if field == 'precio':
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                return None, {field: 'Debe ser un número.'}
            if isinstance(value, float) and not math.isfinite(value):
                return None, {field: 'Debe ser un número finito.'}
        if field == 'disponible' and not isinstance(value, bool):
            return None, {field: 'Debe ser un valor booleano.'}
        normalized[field] = value
    return normalized, None


def _comida_json(comida):
    return {
        'id': comida.pk,
        'title': comida.nombre,
        'description': comida.descripcion,
        'price': float(comida.precio),
        'category': comida.categoria,
        'available': comida.disponible,
    }


def _api_user(request):
    authorization = request.headers.get('Authorization', '')
    scheme, separator, token = authorization.partition(' ')
    if not separator or scheme.lower() != 'token' or not token:
        return None

    try:
        payload = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=getattr(settings, 'API_TOKEN_MAX_AGE', 3600),
        )
        user_id = payload['user_id']
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        return None

    return get_user_model().objects.filter(
        pk=user_id,
        is_active=True,
    ).first()


def _unauthorized():
    return JsonResponse(
        {'error': 'Token ausente, inválido o expirado.'},
        status=401,
    )


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    payload, error = _json_body(request)
    if error:
        return error

    username = payload.get('username')
    password = payload.get('password')
    if not isinstance(username, str) or not username.strip():
        return JsonResponse({'errors': {'username': 'Este campo es obligatorio.'}}, status=400)
    if not isinstance(password, str) or not password:
        return JsonResponse({'errors': {'password': 'Este campo es obligatorio.'}}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': 'Usuario o contraseña incorrectos.'}, status=401)

    max_age = getattr(settings, 'API_TOKEN_MAX_AGE', 3600)
    token = signing.dumps({'user_id': user.pk}, salt=TOKEN_SALT)
    return JsonResponse({
        'token': token,
        'token_type': 'Token',
        'expires_in': max_age,
        'user': {'id': user.pk, 'username': user.get_username()},
    })


@csrf_exempt
def api_comidas(request):
    if request.method not in {'GET', 'POST'}:
        return HttpResponseNotAllowed(['GET', 'POST'])
    if _api_user(request) is None:
        return _unauthorized()

    if request.method == 'GET':
        comidas = Comida.objects.order_by('-id')
        return JsonResponse({'results': [_comida_json(comida) for comida in comidas]})

    payload, error = _json_body(request)
    if error:
        return error
    normalized, validation_error = _normalize_payload(payload)
    if validation_error:
        return JsonResponse({'errors': validation_error}, status=400)
    normalized.setdefault('disponible', True)

    form = ComidaForm(normalized)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)

    comida = form.save()
    response = JsonResponse(_comida_json(comida), status=201)
    response['Location'] = reverse('api_comida_detail', args=[comida.pk])
    return response


@csrf_exempt
def api_comida_detail(request, pk):
    if request.method not in {'GET', 'PUT', 'PATCH', 'DELETE'}:
        return HttpResponseNotAllowed(['GET', 'PUT', 'PATCH', 'DELETE'])
    if _api_user(request) is None:
        return _unauthorized()

    comida = Comida.objects.filter(pk=pk).first()
    if comida is None:
        return JsonResponse({'error': 'Comida no encontrada.'}, status=404)

    if request.method == 'GET':
        return JsonResponse(_comida_json(comida))
    if request.method == 'DELETE':
        comida.delete()
        return JsonResponse({'message': 'Comida eliminada correctamente.'})

    payload, error = _json_body(request)
    if error:
        return error
    normalized, validation_error = _normalize_payload(payload)
    if validation_error:
        return JsonResponse({'errors': validation_error}, status=400)

    if request.method == 'PUT':
        normalized.setdefault('disponible', comida.disponible)
    else:
        normalized = model_to_dict(
            comida,
            fields=('nombre', 'descripcion', 'precio', 'categoria', 'disponible'),
        ) | normalized

    form = ComidaForm(normalized, instance=comida)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)

    return JsonResponse(_comida_json(form.save()))
