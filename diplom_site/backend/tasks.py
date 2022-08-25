import yaml
from django.core.mail import send_mail
from celery import shared_task
from requests import get

from backend.models import Shop, Category, ProductInfo, Product, Parameter, ProductParameter, User


@shared_task()
def send_token_email(email, token):
    """
    Функция асинхронной рассылки токена.
    :param email: Адрес почты.
    :param token: Ключ объекта Token.
    :return:
    """
    send_mail(
        subject="Your New Token",
        message=f"\tNew token: {token}\n\nThank you!",
        recipient_list=[email],
        from_email=None,
        fail_silently=False,
    )
    return 'email sent'


@shared_task()
def load_yaml_task(url, user_id):
    user = User.objects.get(id=user_id)
    stream = get(url).content
    data = yaml.full_load(stream)
    shop, _ = Shop.objects.get_or_create(name=data['shop'], user=user)
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
    return 'yaml loaded'
