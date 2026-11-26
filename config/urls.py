from django.contrib import admin
from django.urls import include, path
from comida import api
from comida import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', api.api_login, name='api_login'),
    path('api/auth/refresh/', api.api_refresh, name='api_refresh'),
    path('api/auth/logout/', api.api_logout, name='api_logout'),
    path('api/openapi.json', api.swagger_spec, name='openapi'),
    path('swagger/', views.swagger_ui, name='swagger_ui'),
    path('api/comidas/', api.api_comidas, name='api_comidas'),
    path(
        'api/comidas/<int:pk>/',
        api.api_comida_detail,
        name='api_comida_detail',
    ),
    path('', include('comida.urls')),
]