# Pranay's part
from django.contrib import admin
from .models import ExchangeRequest, Review


class WorkflowAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExchangeRequest)
class ExchangeAdmin(WorkflowAdmin):
    list_display = ('sender', 'receiver', 'sender_skill', 'receiver_skill', 'status', 'created_at')
    search_fields = ('sender__username', 'receiver__username')
    list_filter = ('status',)


@admin.register(Review)
class ReviewAdmin(WorkflowAdmin):
    list_display = ('reviewer', 'reviewed_user', 'rating', 'created_at')
    search_fields = ('reviewer__username', 'reviewed_user__username', 'comment')
    list_filter = ('rating',)
