from django.contrib import admin

from .models import Comida, UserSession


admin.site.register(Comida)
admin.site.register(UserSession)
