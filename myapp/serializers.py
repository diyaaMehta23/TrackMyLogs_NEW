from rest_framework import serializers
from .models import TokenStorePC

class TokenStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenStorePC
        fields = ['email','token']
