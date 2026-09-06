from django.contrib import admin
from myapp.models import TokenStorePC, GeneratedToken, TokenStoreMobile

# Register your models here.

admin.site.register(TokenStorePC)
admin.site.register(GeneratedToken)
admin.site.register(TokenStoreMobile)

admin.site.site_header = "TrackMyLogs"
admin.site.site_title = "TrackMyLogs Admin Portal"
admin.site.index_title = "Welcome to the TrackMyLogs Admin Dashboard"
