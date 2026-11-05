from django.contrib import admin
from django.urls import include, path
from comida import api


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', api.api_login, name='api_login'),
    path('api/comidas/', api.api_comidas, name='api_comidas'),
    path(
        'api/comidas/<int:pk>/',
        api.api_comida_detail,
        name='api_comida_detail',
    ),
    path('', include('comida.urls')),
]