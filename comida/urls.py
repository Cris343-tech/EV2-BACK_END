from django.urls import path
from . import views


urlpatterns = [

    path(
        '',
        views.inicio,
        name='inicio'
    ),

    path(
        'comidas/',
        views.lista_comidas,
        name='lista_comidas'
    ),

    path(
        'comidas/crear/',
        views.crear_comida,
        name='crear_comida'
    ),

    path(
        'comidas/editar/<int:id>/',
        views.editar_comida,
        name='editar_comida'
    ),

    path(
        'comidas/eliminar/<int:id>/',
        views.eliminar_comida,
        name='eliminar_comida'
    ),

]