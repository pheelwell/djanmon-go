from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin # <-- Import Unfold's ModelAdmin
from .models import User

# Inherit from BOTH BaseUserAdmin and Unfold's ModelAdmin
# The order might matter subtly, but typically putting ModelAdmin first or second works.
# Let's try BaseUserAdmin first, then ModelAdmin.
class UserAdmin(BaseUserAdmin, ModelAdmin): 
    # Your existing customizations remain the same:
    list_display = ('username', 'email', 'first_name', 'last_name', 'level', 'hp', 'attack', 'defense', 'speed', 'is_staff')

    # Fieldsets: This structure should work fine. Unfold respects Django's fieldsets.
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Stats', {'fields': ('level', 'hp', 'attack', 'defense', 'speed', 'attacks')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Stats', {'fields': ('level', 'hp', 'attack', 'defense', 'speed', 'attacks')}),
    )

    # filter_horizontal: This should also work fine with Unfold.
    filter_horizontal = ('attacks', 'groups', 'user_permissions',)
    list_editable = ('level', 'hp', 'attack', 'defense', 'speed')

# No need to unregister if using AUTH_USER_MODEL correctly from the start

# Register your custom User model with the modified UserAdmin configuration
admin.site.register(User, UserAdmin)
