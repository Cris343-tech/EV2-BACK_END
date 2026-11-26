import base64
import hashlib
import hmac
import json
import math
import secrets
import time

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import ComidaForm
from .models import Comida, UserSession


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


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


def _base64url_decode(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def _jwt_encode(payload):
    header = _base64url(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
    body = _base64url(json.dumps(payload, separators=(',', ':')).encode())
    unsigned = f'{header}.{body}'
    signature = hmac.new(settings.SECRET_KEY.encode(), unsigned.encode(), hashlib.sha256).digest()
    return f'{unsigned}.{_base64url(signature)}'


def _jwt_decode(token):
    try:
        header, body, signature = token.split('.')
        unsigned = f'{header}.{body}'
        expected = hmac.new(settings.SECRET_KEY.encode(), unsigned.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_base64url_decode(signature), expected):
            return None
        payload = json.loads(_base64url_decode(body))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None


def _json_body(request):
    if request.content_type != 'application/json':
        return None, JsonResponse({'error': 'El Content-Type debe ser application/json.'}, status=415)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({'error': 'El JSON no es válido.'}, status=400)
    if not isinstance(payload, dict):
        return None, JsonResponse({'error': 'El cuerpo JSON debe ser un objeto.'}, status=400)
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
    if not separator or scheme.lower() != 'bearer' or not token:
        return None
    payload = _jwt_decode(token)
    if payload is None or payload.get('type') != 'access':
        return None
    session = UserSession.objects.filter(
        refresh_jti=payload.get('session'),
        revoked=False,
        expires_at__gt=timezone.now(),
        user_id=payload.get('user_id'),
    ).first()
    if session is None:
        return None
    return get_user_model().objects.filter(pk=payload.get('user_id'), is_active=True).first()


def _unauthorized(message='Token ausente, inválido o expirado.'):
    return JsonResponse({'error': message}, status=401)


def _method_not_allowed(allowed_methods):
    response = JsonResponse(
        {'error': 'Método HTTP no permitido.'},
        status=405,
    )
    response['Allow'] = ', '.join(allowed_methods)
    return response


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return _method_not_allowed(['POST'])
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

    access_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 3600)
    refresh_lifetime = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 604800)
    jti = secrets.token_hex(32)
    now = int(time.time())
    UserSession.objects.create(
        user=user,
        refresh_jti=jti,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        expires_at=timezone.now() + timedelta(seconds=refresh_lifetime),
    )
    access_token = _jwt_encode({
        'user_id': user.pk, 'type': 'access', 'session': jti,
        'iat': now, 'exp': now + access_lifetime,
    })
    refresh_token = _jwt_encode({
        'user_id': user.pk, 'type': 'refresh', 'session': jti,
        'iat': now, 'exp': now + refresh_lifetime,
    })
    return JsonResponse({
        'access': access_token,
        'refresh': refresh_token,
        'token_type': 'Bearer',
        'expires_in': access_lifetime,
        'user': {'id': user.pk, 'username': user.get_username()},
    })


@csrf_exempt
def api_refresh(request):
    if request.method != 'POST':
        return _method_not_allowed(['POST'])
    payload, error = _json_body(request)
    if error:
        return error
    token = payload.get('refresh')
    decoded = _jwt_decode(token) if isinstance(token, str) else None
    if decoded is None or decoded.get('type') != 'refresh':
        return _unauthorized('Refresh Token ausente, inválido o expirado.')
    session = UserSession.objects.filter(
        refresh_jti=decoded.get('session'),
        revoked=False,
        expires_at__gt=timezone.now(),
        user_id=decoded.get('user_id'),
    ).first()
    if session is None:
        return _unauthorized('La sesión fue revocada o expiró.')

    now = int(time.time())
    lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 3600)
    access_token = _jwt_encode({
        'user_id': session.user_id, 'type': 'access', 'session': session.refresh_jti,
        'iat': now, 'exp': now + lifetime,
    })
    return JsonResponse({'access': access_token, 'token_type': 'Bearer', 'expires_in': lifetime})


@csrf_exempt
def api_logout(request):
    if request.method != 'POST':
        return _method_not_allowed(['POST'])
    user = _api_user(request)
    if user is None:
        return _unauthorized()
    authorization = request.headers.get('Authorization', '')
    token = authorization.partition(' ')[2]
    payload = _jwt_decode(token)
    UserSession.objects.filter(refresh_jti=payload.get('session'), user=user).update(revoked=True)
    return JsonResponse({'message': 'Sesión revocada correctamente.'})


@csrf_exempt
def api_comidas(request):
    if request.method not in {'GET', 'POST'}:
        return _method_not_allowed(['GET', 'POST'])
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
    if request.method not in {'GET', 'PUT', 'DELETE'}:
        return _method_not_allowed(['GET', 'PUT', 'DELETE'])
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
    normalized.setdefault('disponible', comida.disponible)
    form = ComidaForm(normalized, instance=comida)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    return JsonResponse(_comida_json(form.save()))


def swagger_spec(request):
    spec = {
        'openapi': '3.0.3',
        'info': {'title': 'FoodShop API', 'version': '1.0.0'},
        'servers': [{'url': '/'}],
        'components': {
            'securitySchemes': {
                'BearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}
            }
        },
        'security': [{'BearerAuth': []}],
        'paths': {
            '/api/auth/login/': {
                'post': {
                    'summary': 'Iniciar sesión y generar JWT',
                    'security': [],
                    'requestBody': {'required': True, 'content': {'application/json': {'schema': {'type': 'object', 'required': ['username', 'password'], 'properties': {'username': {'type': 'string'}, 'password': {'type': 'string'}}}}}},
                    'responses': {'200': {'description': 'Access y Refresh Token'}, '400': {'description': 'Datos inválidos'}, '401': {'description': 'Credenciales incorrectas'}},
                }
            },
            '/api/auth/refresh/': {
                'post': {
                    'summary': 'Renovar Access Token',
                    'security': [],
                    'requestBody': {'required': True, 'content': {'application/json': {'schema': {'type': 'object', 'required': ['refresh'], 'properties': {'refresh': {'type': 'string'}}}}}},
                    'responses': {'200': {'description': 'Nuevo Access Token'}, '401': {'description': 'Refresh inválido'}},
                }
            },
            '/api/comidas/': {
                'get': {'summary': 'Listar comidas', 'responses': {'200': {'description': 'Lista JSON'}, '401': {'description': 'No autorizado'}}},
                'post': {'summary': 'Crear comida', 'responses': {'201': {'description': 'Comida creada'}, '400': {'description': 'Datos inválidos'}, '401': {'description': 'No autorizado'}}},
            },
            '/api/comidas/{id}/': {
                'parameters': [{'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                'get': {'summary': 'Consultar comida', 'responses': {'200': {'description': 'Comida'}, '404': {'description': 'No encontrada'}}},
                'put': {'summary': 'Actualizar comida', 'responses': {'200': {'description': 'Comida actualizada'}, '400': {'description': 'Datos inválidos'}, '404': {'description': 'No encontrada'}}},
                'delete': {'summary': 'Eliminar comida', 'responses': {'200': {'description': 'Comida eliminada'}, '404': {'description': 'No encontrada'}}},
            },
        },
    }
    return JsonResponse(spec)
