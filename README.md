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

Todas las rutas de comidas requieren el encabezado `Authorization: Token <token>`. Para obtenerlo, autentícate con credenciales de un usuario de Django:

```http
POST /api/auth/login/
Content-Type: application/json

{"username": "usuario", "password": "contraseña"}
```

La respuesta contiene el token firmado, el tipo de autorización y su vigencia (una hora por defecto). El token se envía en las siguientes solicitudes:

```http
Authorization: Token <token>
```

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/comidas/` | Lista comidas |
| POST | `/api/comidas/` | Crea una comida |
| GET | `/api/comidas/<id>/` | Consulta una comida |
| PUT | `/api/comidas/<id>/` | Reemplaza sus campos |
| PATCH | `/api/comidas/<id>/` | Actualiza parcialmente |
| DELETE | `/api/comidas/<id>/` | Elimina una comida |

El cuerpo debe ser JSON. Los nombres de campos compatibles con el ejemplo de productos son `title`, `description`, `price` y `category`; también se acepta `available` como booleano opcional. En la base de datos se guardan como `nombre`, `descripcion`, `precio`, `categoria` y `disponible`. El precio debe ser numérico, no negativo y tener hasta dos decimales. Las respuestas de autenticación inválida son HTTP 401, las de validación HTTP 400 y las de registros inexistentes HTTP 404.

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
