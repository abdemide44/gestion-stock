import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Famille, Lot, Produit, Sort


class Command(BaseCommand):
    help = "Populate database with random demo data (familles, produits, lots, sorties)."

    def add_arguments(self, parser):
        parser.add_argument("--familles", type=int, default=8, help="Number of familles to create")
        parser.add_argument("--produits", type=int, default=40, help="Number of produits to create")
        parser.add_argument("--lots", type=int, default=120, help="Number of lots to create")
        parser.add_argument("--sorts", type=int, default=30, help="Number of sorties to create")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing data before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        familles_count = max(1, options["familles"])
        produits_count = max(1, options["produits"])
        lots_count = max(0, options["lots"])
        sorts_count = max(0, options["sorts"])

        if options["reset"]:
            Sort.objects.all().delete()
            Lot.objects.all().delete()
            Produit.objects.all().delete()
            Famille.objects.exclude(nom="-").delete()
            self.stdout.write(self.style.WARNING("Existing data deleted (except famille '-')."))

        today = timezone.now().date()

        # Create familles
        familles = []
        for i in range(1, familles_count + 1):
            fam, _ = Famille.objects.get_or_create(nom=f"Famille-{i:02d}")
            familles.append(fam)

        # Keep fallback family if already present
        fallback = Famille.objects.filter(nom="-").first()
        if fallback:
            familles.append(fallback)

        # Create products
        produits = []
        for i in range(1, produits_count + 1):
            ref = f"PRD-{i:04d}-{random.randint(100, 999)}"
            barcode = "".join(str(random.randint(0, 9)) for _ in range(13))

            # Ensure uniqueness retry
            while Produit.objects.filter(reference=ref).exists():
                ref = f"PRD-{i:04d}-{random.randint(100, 999)}"
            while Produit.objects.filter(barcode=barcode).exists():
                barcode = "".join(str(random.randint(0, 9)) for _ in range(13))

            p = Produit.objects.create(
                nom=f"Produit {i:03d}",
                reference=ref,
                barcode=barcode,
                famille=random.choice(familles),
                nbr_days_alert=random.randint(7, 45),
                nbr_qnt_alert=random.randint(1, 20),
            )
            produits.append(p)

        # Create lots (some expired / near / safe)
        for _ in range(lots_count):
            p = random.choice(produits)
            entry_days_ago = random.randint(0, 180)
            date_entree = today - timedelta(days=entry_days_ago)
            date_fin = date_entree + timedelta(days=random.randint(10, 365))
            quantite = random.randint(0, 120)

            Lot.objects.create(
                produit=p,
                quantite=quantite,
                date_entree=date_entree,
                date_fin=date_fin,
            )

        # Create sortie history (non-blocking demo records)
        if produits:
            for _ in range(sorts_count):
                Sort.objects.create(
                    produit=random.choice(produits),
                    quantite=random.randint(1, 10),
                )

        self.stdout.write(self.style.SUCCESS("Demo data generated successfully."))
        self.stdout.write(
            f"Familles: {Famille.objects.count()} | Produits: {Produit.objects.count()} | "
            f"Lots: {Lot.objects.count()} | Sorties: {Sort.objects.count()}"
        )
