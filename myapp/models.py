from django.db import models

class TokenStorePC(models.Model):
    email = models.CharField(max_length=255)
    token = models.CharField(max_length=255)

    def __str__(self):
        return self.email
    
class GeneratedToken(models.Model):
    username = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    token = models.CharField(max_length=255)

    def __str__(self):
        return self.username
    
class TokenStoreMobile(models.Model):
    email = models.CharField(max_length=255)
    token = models.CharField(max_length=255)

    def __str__(self):
        return self.email


