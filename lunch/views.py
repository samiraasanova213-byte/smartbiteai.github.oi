from datetime import timedelta
from decimal import Decimal
import os
import markdown
from groq import Groq
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count
from django.shortcuts import render, redirect
from django.utils import timezone
from dotenv import load_dotenv
load_dotenv()

from .models import (
    Meal,
    Order,
    WasteRecord,
    Expense,
    Allocation,
    FinanceSettings,
)


def home(request):
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    meals = Meal.objects.filter(available=True)
    cutoff_passed = timezone.localtime().hour >= 9

    if request.method == "POST":
        if cutoff_passed:
            messages.error(
                request,
                "Приём заказов на завтра завершён в 09:00.",
            )
        else:
            name = request.POST.get("student_name", "").strip()
            student_class = request.POST.get("student_class", "").strip()
            meal_id = request.POST.get("meal")

            if not name or not student_class or not meal_id:
                messages.error(request, "Заполни все поля и выбери блюдо.")
            else:
                meal = Meal.objects.filter(
                    id=meal_id,
                    available=True,
                ).first()

                if not meal:
                    messages.error(request, "Это блюдо сейчас недоступно.")
                else:
                    existing = Order.objects.filter(
                        student_name__iexact=name,
                        student_class__iexact=student_class,
                        meal_date=tomorrow,
                    ).exclude(status="cancelled").exists()

                    if existing:
                        messages.error(
                            request,
                            "Для этого ученика уже есть заказ на завтра.",
                        )
                    else:
                        Order.objects.create(
                            student_name=name,
                            student_class=student_class.upper(),
                            meal=meal,
                            meal_date=tomorrow,
                        )
                        messages.success(
                            request,
                            "Заказ успешно принят! Спасибо за выбор.",
                        )
                        return redirect("home")

    return render(
        request,
        "lunch/home.html",
        {
            "meals": meals,
            "tomorrow": tomorrow,
            "cutoff_passed": cutoff_passed,
        },
    )



def menu(request):
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    meals = Meal.objects.filter(available=True)
    cutoff_passed = timezone.localtime().hour >= 9
    if request.method == "POST":
        if cutoff_passed:
            messages.error(
                request,
                "Приём заказов на завтра завершён в 09:00."
            )
        else:
            name = request.POST.get("student_name", "").strip()
            student_class = request.POST.get("student_class", "").strip()
            meal_id = request.POST.get("meal")

            if not name or not student_class or not meal_id:
                messages.error(
                    request,
                    "Заполни все поля и выбери блюдо."
                )
            else:
                meal = Meal.objects.filter(
                    id=meal_id,
                    available=True
                ).first()

                if not meal:
                    messages.error(
                        request,
                        "Это блюдо сейчас недоступно."
                    )
                else:
                    existing = Order.objects.filter(
                        student_name__iexact=name,
                        student_class__iexact=student_class,
                        meal_date=tomorrow,
                    ).exclude(status="cancelled").exists()

                    if existing:
                        messages.error(
                            request,
                            "Для этого ученика уже есть заказ на завтра."
                        )
                    else:
                        Order.objects.create(
                            student_name=name,
                            student_class=student_class.upper(),
                            meal=meal,
                            meal_date=tomorrow,
                        )
                        messages.success(
                            request,
                            "Заказ успешно принят!"
                        )
                        return redirect("menu")

    return render(
        request,
        "lunch/menu.html",
        {
            "meals": meals,
            "tomorrow": tomorrow,
            "cutoff_passed": cutoff_passed,
        }
    )



def staff_check(user):
    return user.is_authenticated and user.is_staff




@login_required
@user_passes_test(staff_check)
def kitchen(request):
    tomorrow = timezone.localdate() + timedelta(days=1)

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        status = request.POST.get("status")

        if status in ["new", "prepared", "cancelled"]:
            order = Order.objects.filter(
                id=order_id,
                meal_date=tomorrow,
            ).first()

            if order:
                order.status = status
                order.save(update_fields=["status"])
                messages.success(request, "Статус заказа обновлён.")

        return redirect("kitchen")

    orders = Order.objects.filter(
        meal_date=tomorrow,
    ).exclude(
        status="cancelled"
    ).select_related(
        "meal"
    ).order_by(
        "meal__name",
        "student_class",
        "student_name",
    )

    totals = orders.values(
        "meal__name"
    ).annotate(
        total=Count("id")
    ).order_by("-total", "meal__name")

    return render(
        request,
        "lunch/kitchen.html",
        {
            "orders": orders,
            "totals": totals,
            "total_orders": orders.count(),
            "tomorrow": tomorrow,
        },
    )



@login_required
@user_passes_test(staff_check)
def economics(request):
    settings_obj = FinanceSettings.objects.first()

    if settings_obj is None:
        settings_obj = FinanceSettings.objects.create()

    total_expenses = Expense.objects.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    total_allocated = Allocation.objects.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    latest_waste = WasteRecord.objects.order_by("-date").first()
    waste_percent = latest_waste.waste_percent if latest_waste else 0
    waste_records = WasteRecord.objects.order_by("-date")[:10]

    return render(request, "lunch/economics.html", {
        "settings_obj": settings_obj,
        "monthly_budget": settings_obj.monthly_budget,
        "estimated_savings": settings_obj.estimated_savings,
        "total_expenses": total_expenses,
        "total_allocated": total_allocated,
        "remaining": max(
            Decimal("0"),
            Decimal(str(settings_obj.estimated_savings)) - total_allocated
        ),
        "latest_waste": latest_waste,
        "waste_records": waste_records,
        "waste_percent": waste_percent,
        "target_waste_percent": settings_obj.target_waste_percent,
    })



@login_required
@user_passes_test(staff_check)
def accounting(request):
    if request.method == "POST":
        record_type = request.POST.get("record_type")

        try:
            if record_type == "waste":
                prepared = Decimal(
                    request.POST.get("prepared_kg", "0")
                )
                wasted = Decimal(
                    request.POST.get("wasted_kg", "0")
                )

                if prepared <= 0 or wasted < 0 or wasted > prepared:
                    raise ValueError

                WasteRecord.objects.create(
                    prepared_kg=prepared,
                    wasted_kg=wasted,
                )
                messages.success(
                    request,
                    "Данные об отходах сохранены."
                )

            elif record_type == "expense":
                title = request.POST.get("title", "").strip()
                category = request.POST.get("category", "").strip()
                amount = Decimal(
                    request.POST.get("amount", "0")
                )

                if not title or not category or amount <= 0:
                    raise ValueError

                Expense.objects.create(
                    title=title,
                    category=category,
                    amount=amount,
                )
                messages.success(request, "Расход сохранён.")

            elif record_type == "allocation":
                title = request.POST.get("title", "").strip()
                category = request.POST.get("category", "").strip()
                amount = Decimal(
                    request.POST.get("amount", "0")
                )

                if not title or not category or amount <= 0:
                    raise ValueError

                Allocation.objects.create(
                    title=title,
                    category=category,
                    amount=amount,
                )
                messages.success(
                    request,
                    "Распределение сохранено."
                )

            else:
                messages.error(
                    request,
                    "Неизвестный тип записи."
                )

        except (ValueError, ArithmeticError):
            messages.error(
                request,
                "Проверь введённые данные. Количество килограммов "
                "и сумма должны быть корректными."
            )

        return redirect("accounting")

    return render(
        request,
        "lunch/accounting.html",
        {
            "expenses": Expense.objects.all()[:20],
            "allocations": Allocation.objects.all()[:20],
            "waste_records": WasteRecord.objects.all()[:20],
            "expenses_total": (
                Expense.objects.aggregate(
                    total=Sum("amount")
                )["total"] or Decimal("0")
            ),
            "allocations_total": (
                Allocation.objects.aggregate(
                    total=Sum("amount")
                )["total"] or Decimal("0")
            ),
        },
    )




def assistant(request):
    chat_history = request.session.get("assistant_messages", [])

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:
            chat_history.append({
                "role": "user",
                "text": user_message
            })

            try:
                api_key = os.environ.get("GROQ_API_KEY")

                if not api_key:
                    raise ValueError("GROQ_API_KEY не найден в настройках.")

                client = Groq(api_key=api_key)

                messages = [
                    {
                        "role": "system",
                        "content": (

        
        "Оформляй ответы красиво и структурированно, "
        "как ChatGPT. Соблюдай следующие правила форматирования:\n"
        "\n"
        "1. Используй Markdown правильно. Не смешивай заголовки, "
        "списки и обычный текст в одну строку.\n"
        "2. Заголовки разделов пиши отдельно, например: "
        "## Ингредиенты и ## Приготовление.\n"
        "3. Каждый ингредиент размещай на отдельной строке "
        "с маркером -.\n"
        "4. Каждый шаг инструкции размещай на отдельном абзаце. "
        "Используй нумерованный список с форматом 1. 2. 3.\n"
        "5. Между заголовком, списком и следующим разделом "
        "оставляй пустую строку.\n"
        "6. Не ставь несколько пунктов на одной строке.\n"
        "7. Не оборачивай заголовки в двойные звёздочки. "
        "Для заголовков используй Markdown-заголовки с #.\n"
        "8. Не используй HTML-теги и не добавляй лишние символы.\n"
        "9. Для рецептов придерживайся порядка: название, "
        "краткое описание, ингредиенты, приготовление, "
        "время приготовления.\n"
        "10. Для простых вопросов отвечай кратко. Для сложных "
        "используй заголовки и списки только там, где они нужны."

)
                    }
                ]

                for item in chat_history[-20:]:
                    messages.append({
                        "role": item["role"],
                        "content": item["text"]
                    })

                response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=messages
)

                answer = (
                    response.choices[0].message.content
                    or "Попробуй задать вопрос ещё раз."
                )

            except Exception as e:
                print("Groq error:", repr(e), flush=True)
                answer = "Не удалось подключиться к Groq. Проверь настройки и терминал VS Code."

            chat_history.append({
                "role": "assistant",
                "text": answer
            })

            chat_history = chat_history[-20:]
            request.session["assistant_messages"] = chat_history

    return render(
        request,
        "lunch/assistant.html",
        {"chat_messages": chat_history}
    )
