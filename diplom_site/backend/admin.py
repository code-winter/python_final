from django.contrib import admin
from backend.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass
