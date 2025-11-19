import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from djmoney.money import Money

from ecommerce_app.models import Category, Product


class Command(BaseCommand):
    help = "Generate 100K product records"

    def handle(self, *args, **options):
        total = 100_000
        batch_size = 5000

        users = list(User.objects.all())
        categories = list(Category.objects.all())

        if not users:
            self.stdout.write(
                self.style.ERROR("❌ No users found. Create at least 1 user.")
            )
            return

        if not categories:
            self.stdout.write(
                self.style.ERROR("❌ No categories found. Create at least 1 category.")
            )
            return

        self.stdout.write(self.style.SUCCESS("🚀 Starting product generation..."))

        for start in range(0, total, batch_size):
            batch = []

            for i in range(batch_size):
                batch.append(
                    Product(
                        name=f"Product {start + i}",
                        category=random.choice(categories),
                        price=Money(random.uniform(10, 1000), "INR"),
                        quantity=random.randint(1, 100),
                        added_by=random.choice(users),
                        created_at=timezone.now(),
                        updated_at=timezone.now(),
                    )
                )

            Product.objects.bulk_create(batch, batch_size=batch_size)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Inserted {start + batch_size} / {total} products..."
                )
            )

        self.stdout.write(self.style.SUCCESS("🎉 Finished creating 100K products!"))
