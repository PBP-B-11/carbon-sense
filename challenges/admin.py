from django.contrib import admin

from .models import Badge, Challenge, CheckIn, Participation, PointEntry, UserBadge

admin.site.register(Badge)
admin.site.register(Challenge)
admin.site.register(Participation)
admin.site.register(CheckIn)
admin.site.register(UserBadge)
admin.site.register(PointEntry)
