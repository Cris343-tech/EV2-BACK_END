import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Comida, UserSession


class ComidaAPITests(TestCase):
    def setUp(self):
        User.objects.create_user(
            username='foodshop-user',
            password='SafePassword123!',
        )
        response = self.client.post(
            reverse('api_login'),
            data=json.dumps({
                'username': 'foodshop-user',
                'password': 'SafePassword123!',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.token = response.json()['access']
        self.refresh = response.json()['refresh']
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.token}'

    def test_api_requires_a_valid_token(self):
        self.client.defaults.pop('HTTP_AUTHORIZATION')
        self.assertEqual(
            self.client.get(reverse('api_comidas')).status_code,
            401,
        )
        self.client.defaults['HTTP_AUTHORIZATION'] = 'Bearer invalid'
        self.assertEqual(
            self.client.get(reverse('api_comidas')).status_code,
            401,
        )

    def test_api_crud_persists_food(self):
        payload = {
            'title': 'Hamburguesa',
            'description': 'Con queso',
            'price': 9.5,
            'category': 'Comida rápida',
        }
        response = self.client.post(
            reverse('api_comidas'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        food_id = response.json()['id']
        self.assertEqual(Comida.objects.get(pk=food_id).precio, Decimal('9.50'))

        self.assertEqual(
            self.client.get(reverse('api_comidas')).json()['results'][0]['title'],
            'Hamburguesa',
        )
        self.assertEqual(
            self.client.get(reverse('api_comida_detail', args=[food_id])).status_code,
            200,
        )

        response = self.client.put(
            reverse('api_comida_detail', args=[food_id]),
            data=json.dumps({
                'title': 'Hamburguesa doble',
                'description': 'Con queso extra',
                'price': 12,
                'category': 'Comida rápida',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comida.objects.get(pk=food_id).nombre, 'Hamburguesa doble')

        response = self.client.delete(reverse('api_comida_detail', args=[food_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.json()['message'], 'Comida eliminada correctamente.')
        self.assertFalse(Comida.objects.filter(pk=food_id).exists())
        self.assertEqual(
            self.client.get(reverse('api_comida_detail', args=[food_id])).status_code,
            404,
        )

    def test_api_rejects_invalid_data_and_missing_items(self):
        response = self.client.post(
            reverse('api_comidas'),
            data=json.dumps({
                'title': 'Precio negativo',
                'description': 'Inválido',
                'price': -1,
                'category': 'Prueba',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comida.objects.exists())

        response = self.client.get(reverse('api_comida_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_returns_json_errors_for_invalid_json_and_methods(self):
        response = self.client.post(
            reverse('api_comidas'),
            data='{',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('error', response.json())

        response = self.client.patch(reverse('api_comida_detail', args=[1]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response['Allow'], 'GET, PUT, DELETE')

    def test_api_login_rejects_invalid_credentials(self):
        response = self.client.post(
            reverse('api_login'),
            data=json.dumps({
                'username': 'foodshop-user',
                'password': 'incorrecta',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_and_logout_tokens(self):
        response = self.client.post(
            reverse('api_refresh'),
            data=json.dumps({'refresh': self.refresh}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        new_access = response.json()['access']

        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {new_access}'
        self.assertEqual(
            self.client.post(reverse('api_logout')).status_code,
            200,
        )
        self.assertFalse(
            UserSession.objects.filter(revoked=False).exists()
        )


class ComidaWebTests(TestCase):
    def test_crud_requires_login_and_invalid_form_does_not_save(self):
        response = self.client.get(reverse('lista_comidas'))
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("lista_comidas")}',
        )

        User.objects.create_user(username='editor', password='SafePassword123!')
        self.assertTrue(self.client.login(username='editor', password='SafePassword123!'))
        response = self.client.post(
            reverse('crear_comida'),
            data={
                'nombre': 'Comida inválida',
                'descripcion': 'Descripción',
                'precio': '-2',
                'categoria': 'Prueba',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comida.objects.exists())

        response = self.client.post(
            reverse('crear_comida'),
            data={
                'nombre': 'Comida válida',
                'descripcion': 'Descripción',
                'precio': '4.50',
                'categoria': 'Prueba',
            },
        )
        self.assertRedirects(response, reverse('lista_comidas'))
        comida = Comida.objects.get()
        self.assertEqual(comida.precio, Decimal('4.50'))
        self.assertTrue(comida.disponible)

    def test_authenticated_pages_and_logout(self):
        User.objects.create_user(username='editor', password='SafePassword123!')
        self.assertTrue(self.client.login(username='editor', password='SafePassword123!'))
        comida = Comida.objects.create(
            nombre='Pizza',
            descripcion='Masa delgada',
            precio=Decimal('8.00'),
            categoria='Comida rápida',
        )

        pages = (
            reverse('inicio'),
            reverse('lista_comidas'),
            reverse('editar_comida', args=[comida.pk]),
            reverse('eliminar_comida', args=[comida.pk]),
        )
        for page in pages:
            with self.subTest(page=page):
                self.assertEqual(self.client.get(page).status_code, 200)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertRedirects(
            self.client.get(reverse('lista_comidas')),
            f'{reverse("login")}?next={reverse("lista_comidas")}',
        )
