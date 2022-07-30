from django.db import models
from django.contrib.auth.models import AbstractUser
USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),

)
CITIES = (
    ('MSK', 'Москва'),
    ('SPB', 'Санкт-Петербург'),
    ('PSK', 'Псков'),
    ('PRM', 'Пермь'),
    ('NSK', 'Новосибирск'),
    ('VSTK', 'Владивосток'),
    ('KGD', 'Калининград'),
)


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']
    email = models.EmailField(unique=True, verbose_name='Электронная почта')
    first_name = models.CharField(verbose_name='Имя', max_length=40)
    last_name = models.CharField(verbose_name='Фамилия', max_length=60)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True, default='Компания')
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True, default='Сотрудник')
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Shop(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.CharField(max_length=100, verbose_name='Адрес сайта', default='Не указан', blank=True)
    state = models.BooleanField(default=True, verbose_name='Прием заказов')
    user = models.OneToOneField(User, verbose_name='Пользователь',
                                blank=True, null=True,
                                on_delete=models.CASCADE)
    placement = models.CharField(verbose_name='Местонахождение', choices=CITIES, default=CITIES[0][0], max_length=10)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Магазины"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=40, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)
    user = models.OneToOneField(User, verbose_name='Пользователь',
                                blank=True, null=True,
                                on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=80, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products', blank=True,
                                 on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = "Список товаров"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    product = models.ForeignKey(Product, verbose_name='Товар', related_name='product_info',
                                blank=True, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='product_info',
                             blank=True, on_delete=models.CASCADE)
    external_id = models.PositiveIntegerField(verbose_name='Внешний идентификатор', default=0)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.PositiveIntegerField(verbose_name='Цена')
    price_rrc = models.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Информация о продуктах"
    constraints = [
        models.UniqueConstraint(fields=['product', 'shop', 'external_id'], name='unique_product_info'),
    ]

    def __str__(self):
        return self.product.name


class Parameter(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')

    class Meta:
        verbose_name = 'Название параметра'
        verbose_name_plural = "Названия параметров"

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='product_parameters', blank=True,
                                     on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', related_name='product_parameters', blank=True,
                                  on_delete=models.CASCADE)
    value = models.CharField(verbose_name='Значение', max_length=100)

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = "Список параметров"
    constraints = [
        models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
    ]

    def __str__(self):
        return f'{self.product_info.product.name} - {self.parameter.name}'


class Contact(models.Model):
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts',
                             blank=True, on_delete=models.CASCADE)
    city = models.CharField(max_length=100, verbose_name='Город', blank=True)
    address = models.CharField(max_length=100, verbose_name='Адрес', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон', blank=True)

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Список контактов'

    def __str__(self):
        return f'Контакт {self.user} ({self.city}, {self.address})'


class Order(models.Model):
    user = models.ForeignKey(User, verbose_name='Пользователь',
                             related_name='orders', blank=True,
                             on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True)
    status_choices = (
        ('basket', 'В корзине'),
        ('new', 'Новый заказ'),
        ('confirmed', 'Подтвержден'),
        ('sent', 'Отправлен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    )
    state = models.CharField(verbose_name='Статус', choices=status_choices, max_length=15, default=status_choices[0][0])
    contact = models.ForeignKey(Contact, verbose_name='Контакт',
                                blank=True, null=True,
                                on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.user}, {self.dt.strftime("%Y-%m-%d, %H:%M:%S")}'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Список заказов'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items', blank=True,
                              on_delete=models.CASCADE)

    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='ordered_items',
                                     blank=True,
                                     on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    total = models.PositiveIntegerField(verbose_name='Сумма', default=0)
    order_number = models.CharField(verbose_name='Номер заказа', blank=True, max_length=50)

    class Meta:
        verbose_name = 'Детали заказа'
        verbose_name_plural = 'Список деталей заказа'
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'product_info'], name='unique_order_item'),
        ]

    def __str__(self):
        return f'Заказ {self.order}'


