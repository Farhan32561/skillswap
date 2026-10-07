# Ankon's part
from django.contrib import admin
from .models import SkillCategory, Skill, SkillOffer, SkillWanted


@admin.register(SkillCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)


@admin.register(SkillOffer, SkillWanted)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'experience_level', 'created_at')
    search_fields = ('user__username', 'skill__name')
    list_filter = ('experience_level',)
