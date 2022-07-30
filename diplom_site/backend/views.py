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

from backend.serializers import UserSerializer, UserUpdateSerializer, ProductInfoSerializer, \
    ProductSerializer, ContactSerializer, OrderSerializer, OrderItemSerializer
from backend.models import Category, ProductInfo, Product, ProductParameter, Parameter, Shop, CITIES, OrderItem, Order


def calculate_delivery_cost(shop_city, buyer_city):
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
            return 200
        shipping_fee = 500
        cost = shipping_fee * distance
        return cost
    else:
        cost = 5000
        return cost


def search_arg_request(request, keyword):
    try:
        result = request.data[keyword]
    except KeyError:
        error_msg = {f"{keyword}": "This field is required"}
        return False, error_msg
    return True, result


class CreateUserView(APIView):
    model = get_user_model()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
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


class UpdateUserView(APIView):
    model = get_user_model()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserUpdateSerializer

    def get(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(f'User updated.')
        else:
            return Response(serializer.errors)


class RefreshToken(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request):
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
    Класс для обновления прайса от поставщика
    """
    def post(self, request):

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = yaml.full_load(stream)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user=request.user)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ListProductView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response({"products": serializer.data})


class ProductDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def get(self, request):
        is_id, product_id = search_arg_request(request, 'id')
        if not is_id:
            return Response(product_id)
        try:
            product_info = ProductInfo.objects.get(product_id=product_id)
        except ObjectDoesNotExist:
            return Response({"error": "ID does not exist"})
        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)


class MakeOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request):
        is_contact, contact = search_arg_request(request, 'contact')
        if not is_contact:
            return Response(contact)
        if not isinstance(contact, dict):
            return Response({"contact": "Invalid format"})

        if contact.get('city'):
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
        order_data = {
            'user': request.user.id,
            'contact': contact.instance.id
        }
        order = OrderSerializer(data=order_data, partial=True)
        if order.is_valid():
            order.save()
        else:
            return Response(order.errors)
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
                product_details_serialized = ProductInfoSerializer(product_details)
                price = int(product_details_serialized.data['price'])
                product_name = product_details_serialized.data['product']['name']
                shop_city = product_details_serialized.data['shop']['placement']
                delivery_cost = calculate_delivery_cost(shop_city, contact.data['city'])
                total = int(price * quantity + delivery_cost)
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
                        'Сумма': price * quantity,
                        'Стоимость доставки': delivery_cost,
                        'Итог': total
                    })
                else:
                    return Response(order_item.errors)
        else:
            return Response({"quantity": "Only positive integers are allowed"})


class ConfirmOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request):
        is_id, order_id = search_arg_request(request, 'id')
        if not is_id:
            return Response(is_id)
        try:
            order_item = OrderItem.objects.get(id=order_id)
        except ObjectDoesNotExist:
            return Response({'id': 'Order with this id does not exist'})
        contact = order_item.order.contact
        err_response = {}
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
        order.state = 'confirmed'
        order.save()
        quantity = order_item.quantity
        product = order_item.product_info
        product.quantity = product.quantity - quantity
        product.save()
        order_number = f'{contact.city}_0{order_id}_{order.dt.strftime("%yx%mx%d")}'
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
                'email': contact.user.email
            }
        })


class ListOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def get(self, request):
        user_id = request.user.id
        orders = OrderItem.objects.filter(order__user__id=user_id).all()
        response = {}
        if orders.exists():
            orders_serialized = OrderItemSerializer(orders, many=True)
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


class InfoOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def get(self, request):
        user_id = request.user.id
        is_id, order_id = search_arg_request(request, 'id')
        if not is_id:
            return Response(is_id)
        try:
            order_item = OrderItem.objects.get(id=order_id)
        except ObjectDoesNotExist:
            return Response({'id': 'Order with this id does not exist'})
