from django import forms

from .models import Comida


class ComidaForm(forms.ModelForm):
    class Meta:
        model = Comida
        fields = ('nombre', 'descripcion', 'precio', 'categoria', 'disponible')
