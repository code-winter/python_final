from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.contrib.auth import get_user_model

from backend.models import ProductInfo, ProductParameter, Parameter, Product, Category, Shop, Contact, Order, OrderItem

UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name')
        write_only_fields = ('password',)
        read_only_fields = ('id', 'is_staff', 'is_superuser')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = UserModel.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    old_password = serializers.CharField(write_only=True)
    type = serializers.CharField()

    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'company', 'type', 'position',
                  'password', 'password2', 'old_password')
        write_only_fields = ('password',)
        read_only_fields = ('id', 'is_staff', 'is_superuser', 'is_active')

    def validate(self, attrs):
        if attrs.get('password'):
            if attrs.get('password2'):
                if attrs['password'] != attrs['password2']:
                    raise serializers.ValidationError({"password": "Password fields didn't match."})
            else:
                raise serializers.ValidationError({"password2": "Required field. "
                                                                "You need to confirm your new password"})

        return attrs

    def validate_old_password(self, value):
        if value:
            user = self.instance
            if not user.check_password(value):
                raise serializers.ValidationError({"old_password": "Old password is not correct"})
        return value

    def validate_type(self, value):
        if value != 'buyer' or value != 'shop':
            return value
        else:
            raise serializers.ValidationError({"type": "Incorrect type of user"})

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            if validated_data.get('old_password'):
                instance.set_password(validated_data['password'])
                validated_data.pop('password')
            else:
                raise serializers.ValidationError({"old_password": "Required field. "
                                                                   "Supply your old password to change it"})
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class ShopSerializer(serializers.ModelSerializer):
    placement = serializers.CharField(source='get_placement_display')

    class Meta:
        model = Shop
        fields = ['name', 'url', 'state', 'placement']


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ['name', ]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Product
        fields = ['id', 'name', 'category']


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ['name']


class ProdParamSerializer(serializers.ModelSerializer):
    parameter = ParameterSerializer()

    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    shop = ShopSerializer()
    params = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductInfo
        fields = ['id', 'model', 'product', 'params', 'shop', 'quantity', 'price', ]

    def get_params(self, obj):
        filtered_data = ProductParameter.objects.all().filter(product_info_id=obj.product_id)
        serializer = ProdParamSerializer(filtered_data, many=True)
        serialized_data = {}
        for param in serializer.data:
            serialized_data.setdefault(param['parameter']['name'], param['value'])
        return serialized_data


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['user', 'city', 'address', 'phone']


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['user', 'state', 'contact']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order', 'product_info', 'quantity', 'total', 'order_number']


