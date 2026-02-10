from django.db import models

# Create your models here.


class Famille(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom


class Produit(models.Model):
    reference = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Référence"
    )

    nom = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nom du produit"
    )

    barcode = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Code-barres"
    )

    famille = models.ForeignKey(
        Famille,
        on_delete=models.PROTECT,
        related_name="produits"
    )

    nbr_days_alert = models.PositiveIntegerField(
        default=30,
        verbose_name="Jours avant alerte péremption"
    )

    nbr_qnt_alert = models.PositiveIntegerField(
        default=1,
        verbose_name="Seuil stock minimum"
    )


    def __str__(self):
        return self.reference


class Lot(models.Model):
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name="lots"
    )

    quantite = models.PositiveIntegerField()

    date_entree = models.DateField()

    date_fin = models.DateField(
        verbose_name="Date de péremption"
    )

    def __str__(self):
        return f"{self.produit.reference} | {self.date_fin}"

    class Meta:
        ordering = ["date_fin"]  # FEFO automatique


class Sort(models.Model):
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name="sorties",
    )
    quantite = models.PositiveIntegerField()
    date_sortie = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.produit.reference} | -{self.quantite} | {self.date_sortie}"
