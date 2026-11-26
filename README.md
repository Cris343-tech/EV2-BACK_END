# FoodShop

Aplicación Django para administrar comidas con persistencia en MySQL, interfaz autenticada y una API JSON. La API sigue el flujo CRUD de productos del ejemplo con DummyJSON, pero opera sobre el modelo local `Comida`.

## Puesta en marcha

1. Crea la base MySQL `foodshop_db` y ajusta usuario, contraseña, host y puerto en `config/settings.py`.
2. Activa el entorno virtual e instala Django y PyMySQL si aún no están disponibles.
   Para producción, define `DJANGO_SECRET_KEY` con un valor secreto y `DJANGO_DEBUG=false`.
3. Ejecuta las migraciones y crea un usuario:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

4. Inicia sesión en `/login/`. Las operaciones de menú requieren una sesión autenticada. Cerrar sesión se realiza mediante POST desde la interfaz.

## API

Todas las rutas de comidas requieren el encabezado `Authorization: Bearer <access-token>`. Para obtener los tokens, autentícate con credenciales de un usuario de Django:

```http
POST /api/auth/login/
Content-Type: application/json

{"username": "usuario", "password": "contraseña"}
```

La respuesta contiene `access`, `refresh`, el tipo de autorización y la vigencia del access token (una hora por defecto).

```http
Authorization: Bearer <access-token>
```

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/comidas/` | Lista comidas |
| POST | `/api/comidas/` | Crea una comida |
| GET | `/api/comidas/<id>/` | Consulta una comida |
| PUT | `/api/comidas/<id>/` | Reemplaza sus campos |
| DELETE | `/api/comidas/<id>/` | Elimina una comida |

Endpoints adicionales:

| Método | Ruta | Acción |
|---|---|---|
| POST | `/api/auth/login/` | Genera Access y Refresh Token |
| POST | `/api/auth/refresh/` | Renueva el Access Token con `{"refresh": "<refresh-token>"}` |
| POST | `/api/auth/logout/` | Revoca la sesión del Access Token |
| GET | `/api/openapi.json` | Entrega la especificación OpenAPI |
| GET | `/swagger/` | Interfaz Swagger |

Las operaciones de escritura reciben y devuelven JSON. Los nombres de campos compatibles con el ejemplo de productos son `title`, `description`, `price` y `category`; también se acepta `available` como booleano opcional. En la base de datos se guardan como `nombre`, `descripcion`, `precio`, `categoria` y `disponible`. El precio debe ser numérico, no negativo y tener hasta dos decimales. Los errores se devuelven como JSON: autenticación inválida HTTP 401, datos inválidos HTTP 400, método no permitido HTTP 405 y registro inexistente HTTP 404.

Ejemplo para crear:

```json
{
  "title": "Hamburguesa",
  "description": "Con queso",
  "price": 9.5,
  "category": "Comida rápida"
}
```

## Pruebas

```powershell
python manage.py test comida
```
