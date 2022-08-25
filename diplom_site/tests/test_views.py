import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from backend.models import User, Product, Category
from rest_framework.authtoken.models import Token

ORDERS = '/orders/'
REGISTER = '/register/'
USERS = '/users/'
PRODUCTS = '/products/'


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_auth(client):
    response = client.post(REGISTER, format='json')
    assert response.status_code == 200
    response = client.post(USERS, format='json')
    assert response.status_code == 401
    response = client.post(ORDERS, format='json')
    assert response.status_code == 401


@pytest.mark.django_db
def test_token(client):
    user = baker.make(User, _quantity=1)[0]
    token = Token.objects.create(user=user).key
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    response = client.get(USERS, format='json')
    assert response.status_code == 200


@pytest.mark.django_db
def test_register(client):
    user = baker.prepare(User, type='shop', _quantity=1)[0]
    data = {
        "password": user.password,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email
    }
    response = client.post(REGISTER, data=data)
    response_data = response.json()
    assert response.status_code == 200
    assert response_data.find('User created') != -1
    data = {
        'username': user.email,
        'password': user.password
    }
    response = client.post('/get_token/', data=data)
    response_data = response.json()
    assert response.status_code == 200
    assert response_data['token']


@pytest.mark.django_db
def test_get_products(client):
    user = baker.make(User, _quantity=1)[0]
    token = Token.objects.create(user=user).key
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    category = Category.objects.create(name='Test cat')
    products = baker.make(Product, category_id=category.id, _quantity=10)
    response = client.get(PRODUCTS)
    response_data = response.json()
    assert response.status_code == 200
    assert response_data.get('products')
    assert len(response_data['products']) == 10



