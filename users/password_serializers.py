"""
Custom serializers for password reset with history validation.
"""
from djoser.serializers import PasswordResetConfirmSerializer as DjoserPasswordResetConfirmSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.conf import settings
from rest_framework.exceptions import ValidationError

User = get_user_model()


class PasswordResetConfirmSerializer(DjoserPasswordResetConfirmSerializer):
    """
    Custom password reset serializer that prevents reusing old passwords.
    """
    
    def validate(self, attrs):
        # Wrap Djoser's validation to catch token errors
        try:
            attrs = super().validate(attrs)
        except ValidationError as e:
            # Check if it's a token error
            error_detail = e.detail
            
            # Handle different error formats from Djoser
            if isinstance(error_detail, dict):
                # Check for token errors in various fields
                if 'token' in error_detail or 'uid' in error_detail:
                    raise serializers.ValidationError({
                        'detail': 'This password reset link is invalid or has expired. Please request a new password reset.',
                        'error_code': 'invalid_or_expired_token'
                    })
                # Check for non_field_errors
                if 'non_field_errors' in error_detail:
                    error_msg = str(error_detail.get('non_field_errors', ''))
                    if 'token' in error_msg.lower() or 'invalid' in error_msg.lower():
                        raise serializers.ValidationError({
                            'detail': 'This password reset link is invalid or has expired. Please request a new password reset.',
                            'error_code': 'invalid_or_expired_token'
                        })
            elif isinstance(error_detail, list):
                error_msg = str(error_detail[0]) if error_detail else ''
                if 'token' in error_msg.lower() or 'invalid' in error_msg.lower() or 'expired' in error_msg.lower():
                    raise serializers.ValidationError({
                        'detail': 'This password reset link is invalid or has expired. Please request a new password reset.',
                        'error_code': 'invalid_or_expired_token'
                    })
            
            # Re-raise the original error if it's not a token error
            raise
        # First, run Djoser's default validation
        attrs = super().validate(attrs)
        
        # Get the user from the uid
        user = self.user
        new_password = attrs['new_password']
        
        # Check against password history
        # Get the number of passwords to check from settings (default: 5)
        password_history_count = getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)
        
        # Check current password
        if user.check_password(new_password):
            raise serializers.ValidationError({
                'detail': 'You cannot reuse your current password. Please choose a different password.',
                'error_code': 'password_reused_current'
            })
        
        # Check password history
        from .models import PasswordHistory
        
        password_history = PasswordHistory.objects.filter(
            user=user
        ).order_by('-created_at')[:password_history_count]
        
        for history_entry in password_history:
            if check_password(new_password, history_entry.password_hash):
                raise serializers.ValidationError({
                    'detail': f'You cannot reuse any of your last {password_history_count} passwords. Please choose a different password.',
                    'error_code': 'password_reused_history'
                })
        
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """
    Custom password change serializer with history validation.
    """
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    re_new_password = serializers.CharField(required=True, write_only=True)
    
    def validate_current_password(self, value):
        """Validate that the current password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError({
                'detail': 'Current password is incorrect.',
                'error_code': 'invalid_current_password'
            })
        return value
    
    def validate(self, attrs):
        """Validate that new passwords match and aren't reused."""
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')
        re_new_password = attrs.get('re_new_password')
        user = self.context['request'].user
        
        # Check if new passwords match
        if new_password != re_new_password:
            raise serializers.ValidationError({
                'detail': 'The two password fields must match.',
                'error_code': 'password_mismatch'
            })
        
        # Check if new password is same as current
        if current_password == new_password:
            raise serializers.ValidationError({
                'detail': 'New password cannot be the same as your current password.',
                'error_code': 'password_unchanged'
            })
        
        # Check against password history
        password_history_count = getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)
        
        from .models import PasswordHistory
        
        password_history = PasswordHistory.objects.filter(
            user=user
        ).order_by('-created_at')[:password_history_count]
        
        for history_entry in password_history:
            if check_password(new_password, history_entry.password_hash):
                raise serializers.ValidationError({
                    'detail': f'You cannot reuse any of your last {password_history_count} passwords. Please choose a different password.',
                    'error_code': 'password_reused_history'
                })
        
        return attrs
    
    def save(self, **kwargs):
        """Save the new password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
