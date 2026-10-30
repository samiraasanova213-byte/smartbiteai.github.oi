from django.db import models
from django.utils import timezone


class Meal(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    student_name = models.CharField(max_length=100)
    student_class = models.CharField(max_length=20)
    meal = models.ForeignKey(Meal, on_delete=models.PROTECT)
    meal_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

    STATUS_CHOICES = [
        ("new", "Новый"),
        ("prepared", "Приготовлен"),
        ("cancelled", "Отменён"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )

    def __str__(self):
        return self.student_name + " — " + self.meal.name


class WasteRecord(models.Model):
    date = models.DateField(default=timezone.localdate)
    prepared_kg = models.DecimalField(max_digits=10, decimal_places=2)
    wasted_kg = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def waste_percent(self):
        if self.prepared_kg == 0:
            return 0

        return self.wasted_kg * 100 / self.prepared_kg


class Expense(models.Model):
    date = models.DateField(default=timezone.localdate)
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.title


class Allocation(models.Model):
    date = models.DateField(default=timezone.localdate)
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.title


class FinanceSettings(models.Model):
    students_per_day = models.PositiveIntegerField(default=500)
    days_per_month = models.PositiveIntegerField(default=20)
    price_per_meal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=100,
    )
    current_waste_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15,
    )
    target_waste_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5,
    )

    @property
    def monthly_budget(self):
        return (
            self.students_per_day
            * self.days_per_month
            * self.price_per_meal
        )

    @property
    def estimated_savings(self):
        difference = max(
            0,
            self.current_waste_percent - self.target_waste_percent,
        )

        return self.monthly_budget * difference / 100