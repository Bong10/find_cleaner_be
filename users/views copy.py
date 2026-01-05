import os
from django.conf import settings 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from django.contrib.auth import get_user_model
from .serializers import (
    CleanerRegistrationSerializer,
    EmployerRegistrationSerializer,
    AdminRegistrationSerializer,
    RoleSerializer,
    UserSerializer,
)
from .models import User, Role
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.template.loader import render_to_string
import random
import jwt

User = get_user_model()

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})

class CleanerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]  
    serializer_class = CleanerRegistrationSerializer

    def post(self, request):
        serializer = CleanerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            cleaner = serializer.save()
            token = jwt.encode({'user_id': cleaner.user.id}, 'secret_key', algorithm='HS256')
            token_url = f'http://localhost:8000/api/users/activate/{token}'

            # Send the token via email
            try:
                subject = 'Activate your account'
                template_path = os.path.join(settings.BASE_DIR, 'users', 'templates', 'jwt_email_template.html')
                html_content = render_to_string(template_path, {'name': cleaner.user.name, 'token_url': token_url})
                text_content = 'To activate your account, please click the following link: {}'.format(token_url)

                email = EmailMultiAlternatives(subject, text_content, 'geordannoubissie@gmail.com', [cleaner.user.email])
                email.attach_alternative(html_content, "text/html")

                # Attach the image as an inline attachment
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.svg')
                with open(logo_path, 'rb') as f:
                    logo = MIMEBase('image', 'svg+xml')
                    logo.set_payload(f.read())
                    encoders.encode_base64(logo)
                    logo.add_header('Content-ID', '<logo>')
                    logo.add_header('Content-Disposition', 'inline', filename='logo.svg')
                    email.attach(logo)
                email.send()
            except Exception as e:
                return Response({"message": f"Error sending token: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": "Cleaner created. An email has been sent to activate the account."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    

class EmployerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]  
    serializer_class = EmployerRegistrationSerializer

    def post(self, request):
        serializer = EmployerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            employer = serializer.save()
            token = jwt.encode({'user_id': employer.user.id}, 'secret_key', algorithm='HS256')
            token_url = f'http://localhost:8000/api/users/activate/{token}'

            # Send the token via email
            try:
                subject = 'Activate your account'
                template_path = os.path.join(settings.BASE_DIR, 'users', 'templates', 'jwt_email_template.html')
                html_content = render_to_string(template_path, {'name': employer.user.name, 'token_url': token_url})
                text_content = 'To activate your account, please click the following link: {}'.format(token_url)

                email = EmailMultiAlternatives(subject, text_content, 'geordannoubissie@gmail.com', [employer.user.email])
                email.attach_alternative(html_content, "text/html")

                # Attach the image as an inline attachment
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.svg')
                with open(logo_path, 'rb') as f:
                    logo = MIMEBase('image', 'svg+xml')
                    logo.set_payload(f.read())
                    encoders.encode_base64(logo)
                    logo.add_header('Content-ID', '<logo>')
                    logo.add_header('Content-Disposition', 'inline', filename='logo.svg')
                    email.attach(logo)

                email.send()
            except Exception as e:
                return Response({"message": f"Error sending token: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": "Employer created. An email has been sent to activate the account."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class AdminRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]  
    serializer_class = AdminRegistrationSerializer

    def post(self, request):
        serializer = AdminRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            admin = serializer.save()
            token = jwt.encode({'user_id': admin.user.id}, 'secret_key', algorithm='HS256')
            token_url = f'http://localhost:8000/api/users/activate/{token}'

            # Send the token via email
            try:
                subject = 'Activate your account'
                template_path = os.path.join(settings.BASE_DIR, 'users', 'templates', 'jwt_email_template.html')
                html_content = render_to_string(template_path, {'name': admin.user.name, 'token_url': token_url})
                text_content = 'To activate your account, please click the following link: {}'.format(token_url)

                email = EmailMultiAlternatives(subject, text_content, 'geordannoubissie@gmail.com', [ admin.user.email])
                email.attach_alternative(html_content, "text/html")

                # Attach the image as an inline attachment
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.svg')
                with open(logo_path, 'rb') as f:
                    logo = MIMEBase('image', 'svg+xml')
                    logo.set_payload(f.read())
                    encoders.encode_base64(logo)
                    logo.add_header('Content-ID', '<logo>')
                    logo.add_header('Content-Disposition', 'inline', filename='logo.svg')
                    email.attach(logo)

                email.send()
            except Exception as e:
                return Response({"message": f"Error sending token: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": "Admin created. An email has been sent to activate the account."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class RoleManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]  

    def get(self, request):
        """
        Retrieve all available roles.
        """
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new role.
        """
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ActivateUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            payload = jwt.decode(token, 'secret_key', algorithms=['HS256'])
            user_id = payload['user_id']
            user = User.objects.get(id=user_id)

            if not user.is_active:
                user.is_active = True
                user.save()
                return Response({'message': 'Account successfully activated.'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Account already activated.'}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Activation link expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid activation token.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
