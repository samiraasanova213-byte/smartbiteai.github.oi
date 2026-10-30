from django.contrib import admin
from .models import (
    Meal,
    Order,
    WasteRecord,
    Expense,
    Allocation,
    FinanceSettings,
)

admin.site.register(Meal)
admin.site.register(Order)
admin.site.register(WasteRecord)
admin.site.register(Expense)
admin.site.register(Allocation)
admin.site.register(FinanceSettings)