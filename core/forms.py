from django import forms
from .models import Produit, Famille, Lot

from django.utils import timezone



class LotForm(forms.ModelForm):

    class Meta:
        model = Lot
        fields = [
            "produit",
            "date_entree",
            "date_fin",
            "quantite",
        ]
        widgets = {
            "produit": forms.Select(attrs={"class": "form-select"}),
            "date_entree": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
            ),
            "quantite": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
        }

    def clean_date_entree(self):
        """
        Si la date d'entrée est vide, on met la date d'aujourd'hui.
        """
        date_entree = self.cleaned_data.get("date_entree")
        if not date_entree:
            return timezone.now().date()
        return date_entree

class ProductForm(forms.ModelForm):

    class Meta:
        model = Produit
        fields = [
            "nom",
            "reference",
            "famille",
            "barcode",
            "nbr_qnt_alert",
            "nbr_days_alert",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "famille": forms.Select(attrs={"class": "form-select"}),
            "barcode": forms.TextInput(attrs={"class": "form-control"}),
            "nbr_qnt_alert": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "nbr_days_alert": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def clean_barcode(self):
        return self.cleaned_data["barcode"].strip()


class FamilleForm(forms.ModelForm):
    class Meta:
        model = Famille
        fields = [
            "nom",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
        }
    def clean_nom(self):
        return self.cleaned_data["nom"].strip()


class MovementForm(forms.Form):
    code = forms.CharField(
        label="Reference / code-barres",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "barcode-input",
                "placeholder": "Scanner ou taper reference / barcode",
                "autofocus": True,
            }
        ),
    )
    quantite = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 1,
            }
        ),
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip()
