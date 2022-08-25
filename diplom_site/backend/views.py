from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from requests import get
import yaml
from django.core.validators import URLValidator
from django.http import JsonResponse
from rest_framework import permissions
from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets

from backend.serializers import UserSerializer, UserUpdateSerializer, ProductInfoSerializer, \
    ProductSerializer, ContactSerializer, OrderSerializer, OrderItemSerializer
from backend.models import Category, ProductInfo, Product, ProductParameter, Parameter, Shop, CITIES, OrderItem, User
from backend.tasks import send_token_email, load_yaml_task


def calculate_delivery_cost(shop_city, buyer_city):
    """
    Функция для расчета стоимости доставки. Доставка рассчитывается от количества узлов между городами.
    :param shop_city: местонахождение магазина.
    :param buyer_city: местонахождение покупателя.
    :return: возвращает int() значение суммы
    """
    if buyer_city in dict(CITIES).values():
        shop_index = 0
        buyer_index = 0
        for index, city in enumerate(dict(CITIES).values()):
            if shop_city == city:
                shop_index = index
        for index, city in enumerate(dict(CITIES).values()):
            if buyer_city == city:
                buyer_index = index
        distance = shop_index - buyer_index
        if distance < 0:
            distance *= -1
        if distance == 0:
            # если покупатель и магазин находятся в одном городе
            return 200
        shipping_fee = 500
        cost = shipping_fee * distance
        return cost
    else:
        cost = 5000
        return cost


def search_arg_request(request, keyword):
    """
    Функция для упрощенного поиска аргументов в теле запроса.
    Возвращает булевый параметр и значение, если значения нет - выдает строку.
    :return: Boolean
    """
    try:
        result = request.data[keyword]
    except KeyError:
        error_msg = {f"{keyword}": "This field is required"}
        return False, error_msg
    return True, result


class RegisterView(viewsets.ViewSet):
    """
    View-класс для создания пользователей.
    Принимает ФИО, телефон, электронную почту, пароль.
    """
    model = get_user_model()
    serializer_class = UserSerializer

    def create(self, request):
        """
        Функция для создания пользователя.
        :param request: Данные для создания записи пользователя: ФИО, почта, пароль, телефон.
        :return:
        """
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(f'User created. '
                            f'  Email: {serializer.data["email"]}'
                            f'  First name:{serializer.data["first_name"]}'
                            f'  Last name: {serializer.data["last_name"]}'
                            )
        else:
            return Response(serializer.errors)


class UserUpdateView(viewsets.ViewSet):
    """
    View-класс для изменения пользователей. Допускается изменение только своего пользователя и только для
    авторизированных пользователей. Допускается частичное изменение, а также просмотр личных данных.
    """
    model = get_user_model()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserUpdateSerializer
    queryset = User.objects.all()

    def list(self, request):
        """
        Функция для отображения текущих данных пользователя
        :param request:
        :return: JSON
        """
        user = request.user
        serializer = UserUpdateSerializer(user)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """
        Функция для изменения данных пользователя
        :param request: Данные для изменения полей пользователя.
        :param pk: ID пользователя.
        :return: JSOM
        """
        queryset = User.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        # если юзер не совпадает с юзером из запроса
        if user != request.user:
            return Response({"error": "Not authorized"})
        # передаем partial=True, чтобы не требовать полную информацию от пользователя каждый раз
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(f'User updated.')
        else:
            return Response(serializer.errors)


class RefreshToken(APIView):
    """
    View-класс для обновления токена доступа. Принимает логин и пароль.
    """
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = UserSerializer

    def post(self, request):
        """
        Функция для обновления токена доступа.
        :param request: Должен содержать логин и пароль.
        :return: Объект токена.
        """
        user = request.user
        if request.data.get('username'):
            if request.auth.user.email != request.data.get('username'):
                return Response({"username": "User with that email-token does not exist"})
            if request.data.get('password'):
                if not user.check_password(request.data['password']):
                    return Response({"password": "Incorrect password"})
                old_token = request.auth
                Token.objects.filter(key=old_token).delete()
                token = Token.objects.create(user=user)
                # дублируем токен на указанную почту
                send_token_email.delay(user.email, token.key)
                return Response({
                    'token': token.key,
                })
            else:
                return Response({"password": "Required field"})
        else:
            return Response({"username": "Required field"})


class PartnerUpdate(APIView):
    permission_classes = [permissions.IsAuthenticated, ]
    """
    Класс для обновления прайса от поставщика. Принимает ссылку на .yaml-файл с информацией.
    """
    def post(self, request):
        """
        Функция для обработки .yaml файла
        :param request: ссылка на .yaml файл
        :return: JSON
        """

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Shops only'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                load_yaml_task.delay(url, request.user.id)
                return JsonResponse({'Status': 'Files are being loaded'})

        return JsonResponse({'Status': False, 'Errors': 'All required arguments were not provided'})


class ProductView(viewsets.ViewSet):
    """
    View для просмотра и изменения параметров продуктов. Доступ только для аутентифицированных пользователей.
    """
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.all()

    def list(self, request):
        """
        Функция для просмотра всех продуктов в магазинах
        :param request:
        :return: JSON
        """
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response({"products": serializer.data})

    def retrieve(self, request, pk=None):
        """
        Функция для отображения детальной информации продукта
        :param request:
        :param pk: ID продукта
        :return: JSON
        """
        queryset = ProductInfo.objects.all()
        product_info = get_object_or_404(queryset, pk=pk)
        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)


class OrderView(viewsets.ViewSet):
    """
    View для просмотра и изменения заказов. Доступ только для аутентифицированных пользователей.
    """
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = OrderItemSerializer
    queryset = OrderItem.objects.all()

    def list(self, request):
        """
        Функция для отображения всех заказов пользователя
        :param request:
        :return: JSON
        """
        user_id = request.user.id
        orders = OrderItem.objects.filter(order__user__id=user_id).all()
        response = {}
        if orders.exists():
            orders_serialized = OrderItemSerializer(orders, many=True)
            # перебираем все заказы для более читаемой информации в Response
            for pos, item in enumerate(orders_serialized.data):
                response.setdefault(pos, {
                    'id': orders[pos].id,
                    'order_number': item['order_number'],
                    'date_created': orders[pos].order.dt.strftime("%Y.%m.%d"),
                    'total': item['total'],
                    'state': orders[pos].order.state
                })
            return Response({'orders': response})
        else:
            return Response({'orders': 'No orders found'})

    def retrieve(self, request, pk=None):
        """
        Функция для получения деталей заказа
        :param request:
        :param pk: ID заказа
        :return: JSON
        """
        user_id = request.user.id
        queryset = OrderItem.objects.all()
        order_item = get_object_or_404(queryset, pk=pk)
        order_owner = order_item.order.user.id
        if user_id != order_owner:
            return Response({'error': 'Permission denied'})
        response = {
            'order_number': order_item.order_number,
            'date_created': order_item.order.dt.strftime("%Y.%m.%d"),
            'state': order_item.order.state,
            'order_details': {
                'product_name': order_item.product_info.product.name,
                'shop': order_item.product_info.shop.name,
                'price': order_item.product_info.price,
                'quantity': order_item.quantity,
                'total': order_item.total
            },
            'contact_details': {
                'city': order_item.order.contact.city,
                'address': order_item.order.contact.address,
                'phone': order_item.order.contact.phone,
                'email': order_item.order.contact.user.email,
                'person': f'{order_item.order.contact.user.first_name} {order_item.order.contact.user.last_name}'
            }
        }
        return Response(response)

    def create(self, request):
        """
        Функция для создания заказа.
        :param request: JSON-объект с данными контактов и количеством продуктов для заказа.
        :return: JSON
        """
        is_contact, contact = search_arg_request(request, 'contact')
        if not is_contact:
            return Response(contact)
        if not isinstance(contact, dict):
            return Response({"contact": "Invalid format"})

        if contact.get('city'):
            # создаем объект Contact
            contact_data = {
                'user': request.user.id,
                'city': contact['city'],
                'address': contact.get('address', 'Не указан'),
                'phone': contact.get('phone', 'Не указан')

            }
            contact = ContactSerializer(data=contact_data)
            if contact.is_valid():
                contact.save()
            else:
                return Response(contact.errors)
        else:
            return Response({"contact": {"city": "This field is required"}})
        # создаем объект Order
        order_data = {
            'user': request.user.id,
            'contact': contact.instance.id
        }
        order = OrderSerializer(data=order_data, partial=True)
        if order.is_valid():
            order.save()
        else:
            return Response(order.errors)
        # ищем количество в запросе
        is_quantity, quantity = search_arg_request(request, 'quantity')
        if not is_quantity:
            return Response(quantity)
        if isinstance(quantity, int) and quantity > 0:
            is_product, product_info_id = search_arg_request(request, 'product_info')
            if not is_product:
                return Response(product_info_id)
            else:
                try:
                    product_details = ProductInfo.objects.get(product_id=product_info_id)
                except ObjectDoesNotExist:
                    return Response({"product_info": "ID does not exist"})
                # получаем нужную информацию из созданных объектов
                product_details_serialized = ProductInfoSerializer(product_details)
                price = int(product_details_serialized.data['price'])
                product_name = product_details_serialized.data['product']['name']
                shop_city = product_details_serialized.data['shop']['placement']
                delivery_cost = calculate_delivery_cost(shop_city, contact.data['city'])
                total = int(price * quantity + delivery_cost)
                # создаем объект OrderItem
                order_item_data = {
                    'order': order.instance.id,
                    'product_info': product_details_serialized.instance.id,
                    'quantity': quantity,
                    'total': total
                }
                order_item = OrderItemSerializer(data=order_item_data)
                if order_item.is_valid():
                    order_item.save()
                    return Response({
                        'id': order_item.instance.id,
                        'status': 'В корзине',
                        'product': {
                            'name': product_name,
                            'price': price,
                            'shop_location': shop_city,
                            'quantity': quantity
                        },
                        'sum': price * quantity,
                        'delivery_cost': delivery_cost,
                        'total': total
                    })
                else:
                    return Response(order_item.errors)
        else:
            return Response({"quantity": "Only positive integers are allowed"})

    def partial_update(self, request, pk=None):
        """
        Функция для подтверждения заказа.
        :param request: JSON-объект с данными контактов
        :param pk: ID заказа
        :return: JSON
        """
        queryset = OrderItem.objects.all()
        order_item = get_object_or_404(queryset, pk=pk)
        contact = order_item.order.contact
        err_response = {}  # заглушка для описания ошибок для выдачи Response
        if contact.address == 'Не указан' and not request.data.get('address'):
            err_response.setdefault('address', 'Fill this field to confirm')
        if contact.phone == 'Не указан' and not request.data.get('phone'):
            err_response.setdefault('phone', 'Fill this field to confirm')
        if err_response.get('phone') or err_response.get('address'):
            return Response(err_response)
        address = request.data.get('address')
        phone = request.data.get('phone')
        contact.address = address
        contact.phone = phone
        contact.save()
        order = order_item.order
        # меняем статус заказа
        order.state = 'confirmed'
        order.save()
        quantity = order_item.quantity
        product = order_item.product_info
        product.quantity = product.quantity - quantity
        if product.quantity < 0:
            return Response({"error": "Sorry, there is less items that you want"})
        product.save()
        # номер заказа имеет формат 'город_0(айди_заказа)_дата'
        order_number = f'{contact.city}_0{pk}_{order.dt.strftime("%yx%mx%d")}'
        order_item.order_number = order_number
        order_item.save()
        return Response({
            'status': 'OK',
            'order_number': order_number,
            'product': {
                'name': product.product.name,
                'shop': product.shop.name,
                'price': product.price,
                'quantity': quantity,
                'total': order_item.total
            },
            'user_info': {
                'address': contact.address,
                'phone': contact.phone,
                'email': contact.user.email,
                'person': f'{contact.user.first_name} {contact.user.last_name}'
            }
        })
