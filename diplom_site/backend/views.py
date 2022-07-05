from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from backend.serializers import UserSerializer, UserUpdateSerializer


class CreateUserView(APIView):
    model = get_user_model()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
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
