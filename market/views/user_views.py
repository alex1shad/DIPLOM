from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from django.db.models.query import QuerySet

from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from market.models import ConfirmEmailToken, Contact, User
from market.serializers import UserSerializer, ContactSerializer
from market.tasks import send_token_to_email_task, send_simple_mail_task


class RegisterAccount(APIView):
    """
    Класс регистрации пользователей.
    """
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    if request.data.get('type') == 'shop':
                        user.type = 'shop'
                    user.save()

                    if request.data.get('test') == 'test':
                        # Для тестирования возвращаем:
                        return JsonResponse({'Status': True, 'Test': 'Passed'})

                    else:
                        # Отправить пользователю email (с токеном) для его подтверждения, используя Celery
                        send_token_to_email_task.delay(user_id=user.id,
                                                       title='Django-API-market: Mail confirmation token')
                        return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})


class ConfirmAccount(APIView):
    """
    Класс подтверждения почтового адреса.
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})
        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})


class LoginAccount(APIView):
    """
    Класс авторизации пользователей
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
                return JsonResponse({'Status': False, 'Errors': 'Требуется подтверждение email'})
            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})
        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})


class AccountDetails(APIView):
    """
    Класс работы данными пользователя
    """
    permission_classes = [IsAuthenticated]

    # Получение данных
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование данных.
    def post(self, request, *args, **kwargs):
        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

                if 'test' not in request.data:
                    send_simple_mail_task.delay(user_id=request.user.id,
                                                title='Django-API-market: Изменение пароля',
                                                message='Пароль был изменен')

        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            if request.data['email'] != request.user.email:
                request.user.is_active = False
                if request.data.get('test') == 'test':
                    user_serializer.save()
                    return JsonResponse({'Status': True,
                                         'Test': 'Passed',
                                         'Details': 'Изменился email. Нужно подтверждение'})
                send_token_to_email_task.delay(user_id=request.user.id,
                                               title='Django-API-market: Mail confirmation token')
                user_serializer.save()
                return JsonResponse({'Status': True, 'Details': 'Изменился email. Нужно подтверждение'})
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class ContactView(ModelViewSet):
    """
    Класс работы с контактами покупателей
    """
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if {'city', 'street', 'phone', 'house'}.issubset(request.data):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data)
        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        if isinstance(queryset, QuerySet):
            queryset = queryset.all()
        return queryset

    def update(self, request, *args, **kwargs):
        if {'city', 'street', 'phone', 'house'}.issubset(request.data):
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}
            return Response(serializer.data)
        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})


class ResetPassword(APIView):
    """
    Класс сброса пароля.
    """
    def post(self, request, *args, **kwargs):
        if {'email'}.issubset(request.data):
            user = User.objects.get(email=request.data['email'])
            if user:
                if 'test' not in request.data:
                    send_token_to_email_task.delay(user_id=user.id,
                                                   title='Django-API-market: Reset password token')
                    return JsonResponse({'Status': True})
                return JsonResponse({'Status': True,
                                     'Test': 'Passed',
                                     'Details': 'Пользователь найден, пароль может быть сброшен'})
            return JsonResponse({'Status': False, 'Errors': 'Пользователь с таким email не существует'})
        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})


class ResetPasswordConfirm(APIView):
    """
    Класс подтверждения сброса пароля
    """
    def post(self, request, *args, **kwargs):
        if {'token', 'email', 'password'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                try:
                    validate_password(request.data['password'])
                except Exception as password_error:
                    error_array = []
                    # noinspection PyTypeChecker
                    for item in password_error:
                        error_array.append(item)
                    return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
                else:
                    token.user.set_password(request.data['password'])
                    token.user.save()
                    token.delete()
                    if 'test' not in request.data:
                        send_simple_mail_task.delay(user_id=token.user.id,
                                                    title='Django-API-market: Изменение пароля',
                                                    message='Пароль был изменен')
                        return JsonResponse({'Status': True})
                    return JsonResponse({'Status': True, 'Test': 'Passed'})

            return JsonResponse({'Status': False, 'Errors': 'Токен или email указан неверно'})

        return JsonResponse({'Status': False, 'Errors': 'Укажите все аргументы'})
