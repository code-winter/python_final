from django.contrib import admin
from backend.models import User, Shop, Category, Product, ProductInfo, ProductParameter, Contact


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass


@admin.register(ProductInfo)
class ProdInfoAdmin(admin.ModelAdmin):
    pass


@admin.register(ProductParameter)
class ProdParamAdmin(admin.ModelAdmin):
    pass


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    pass

