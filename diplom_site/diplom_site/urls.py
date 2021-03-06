"""diplom_site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework.authtoken import views

from backend.views import CreateUserView, UpdateUserView, PartnerUpdate, ListProductView, ProductDetailsView, \
    RefreshToken, MakeOrderView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('get_token/', views.obtain_auth_token),
    path('refresh_token/', RefreshToken.as_view()),
    path('register/', CreateUserView.as_view()),
    path('user/', UpdateUserView.as_view()),
    path('partner_update/', PartnerUpdate.as_view()),
    path('products/', ListProductView.as_view()),
    path('products/details/', ProductDetailsView.as_view()),
    path('products/order/', MakeOrderView.as_view())
]
