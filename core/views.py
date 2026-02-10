import time
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect
from datetime import date

# Create your views here.
from django.db.models import Sum

from .forms import ProductForm, FamilleForm, LotForm, MovementForm
from .models import Famille, Produit, Lot, Sort


DATA_VERSION_CACHE_KEY = "core_data_version"


def get_data_version():
    return int(cache.get(DATA_VERSION_CACHE_KEY, 1))


def bump_data_version():
    cache.set(DATA_VERSION_CACHE_KEY, get_data_version() + 1, None)
def dashboard(request):
    active_page = "dashboard"
    today = date.today()

    produits_qs = (
        Produit.objects
        .select_related("famille")
        .annotate(stock_total=Sum("lots__quantite"))
    )

    product_states = []
    stock_alert_count = 0
    expiry_alert_count = 0
    critical_products_count = 0

    for p in produits_qs:
        stock = p.stock_total or 0

        if stock <= 0:
            stock_level = "danger"
            stock_label = "Rupture de stock"
            stock_alert_count += 1
        elif stock <= p.nbr_qnt_alert:
            stock_level = "near"
            stock_label = "Seuil de stock atteint"
            stock_alert_count += 1
        else:
            stock_level = "ok"
            stock_label = "Stock normal"

        if stock <= 0:
            exp_level = "ok"
            exp_label = "Pas de stock"
        else:
            next_lot = p.lots.filter(quantite__gt=0).order_by("date_fin").first()
            if not next_lot:
                exp_level = "ok"
                exp_label = "Aucune date de péremption"
            else:
                days_left = (next_lot.date_fin - today).days
                if days_left < 0:
                    exp_level = "danger"
                    exp_label = "Produit expiré"
                    expiry_alert_count += 1
                elif days_left == 0:
                    exp_level = "danger"
                    exp_label = "Expire aujourd’hui"
                    expiry_alert_count += 1
                elif days_left <= p.nbr_days_alert:
                    exp_level = "near"
                    exp_label = f"Expire dans {days_left} jour(s)"
                    expiry_alert_count += 1
                else:
                    exp_level = "ok"
                    exp_label = f"Expire dans {days_left} jour(s)"

        if stock_level == "danger" or exp_level == "danger":
            critical_products_count += 1

        product_states.append(
            {
                "nom": p.nom or "-",
                "reference": p.reference,
                "barcode": p.barcode,
                "stock_level": stock_level,
                "stock_label": stock_label,
                "exp_level": exp_level,
                "exp_label": exp_label,
            }
        )

    context = {
        "active_page": active_page,
        "total_alerts": stock_alert_count + expiry_alert_count,
        "stock_alert_count": stock_alert_count,
        "expiry_alert_count": expiry_alert_count,
        "critical_products_count": critical_products_count,
        "product_states": product_states,
    }
    return render(request, "dashboard.html", context)


def updates_stream(request):
    def stream():
        last_sent = get_data_version()
        yield f"event: init\ndata: {last_sent}\n\n"
        while True:
            time.sleep(1)
            current = get_data_version()
            if current != last_sent:
                last_sent = current
                yield f"event: data-update\ndata: {current}\n\n"

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def products(request):
    active_page = "products"
    selected_famille_id = (request.GET.get("famille") or "").strip()

    # -------------------------
    # Form ajout produit
    # -------------------------
    if request.method == "POST":
        action = request.POST.get("action", "add_product")

        if action == "delete_product":
            product_id = request.POST.get("product_id")
            product = Produit.objects.filter(id=product_id).first()
            if not product:
                messages.error(request, "Produit introuvable.")
                return redirect("products")

            product_ref = product.reference
            lots_count = product.lots.count()
            product.delete()
            bump_data_version()
            messages.success(
                request,
                f"Produit {product_ref} supprime avec {lots_count} lot(s) associe(s).",
            )
            return redirect("products")

        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            bump_data_version()
            return redirect("products")
    else:
        form = ProductForm()

    # -------------------------
    # Produits + stock total
    # -------------------------
    produits_qs = (
        Produit.objects
        .select_related("famille")
        .annotate(stock_total=Sum("lots__quantite"))
    )
    if selected_famille_id:
        produits_qs = produits_qs.filter(famille_id=selected_famille_id)

    today = date.today()
    items = []

    for p in produits_qs:
        stock = p.stock_total or 0

        # ---------- Statut du stock ----------
        if stock <= 0:
            stock_level = "danger"
            stock_label = "Rupture de stock"
        elif stock <= p.nbr_qnt_alert:
            stock_level = "near"
            stock_label = "Seuil de stock atteint"
        else:
            stock_level = "ok"
            stock_label = "Stock normal"

        # ---------- Statut de péremption ----------
        # Si le stock est nul, on ignore le statut d'expiration.
        if stock <= 0:
            exp_level = "ok"
            exp_label = "Pas de stock"
        else:
            next_lot = p.lots.filter(quantite__gt=0).order_by("date_fin").first()

            if not next_lot:
                exp_level = "ok"
                exp_label = "Aucune date de péremption"
            else:
                days_left = (next_lot.date_fin - today).days

                if days_left < 0:
                    exp_level = "danger"
                    exp_label = "Produit expiré"
                elif days_left == 0:
                    exp_level = "danger"
                    exp_label = "Expire aujourd’hui"
                elif days_left <= p.nbr_days_alert:
                    exp_level = "near"
                    exp_label = f"Expire dans {days_left} jour(s)"
                else:
                    exp_level = "ok"
                    exp_label = f"Expire dans {days_left} jour(s)"

        items.append({
            "id": p.id,
            "nom": p.nom,
            "reference": p.reference,
            "barcode": p.barcode,
            "famille": p.famille,
            "stock_total": stock,
            "nbr_qnt_alert": p.nbr_qnt_alert,
            "nbr_days_alert": p.nbr_days_alert,
            "stock_level": stock_level,
            "stock_label": stock_label,
            "exp_level": exp_level,
            "exp_label": exp_label,
        })
    familles = Famille.objects.all().order_by("nom")

    return render(
        request,
        "products.html",
        {
            "active_page": active_page,
            "products": items,   # ⚠️ items وليس queryset
            "form": form,
            "familles": familles,
            "selected_famille_id": selected_famille_id,
        }
    )


def product_edit(request, product_id):
    active_page = "products"
    product = Produit.objects.filter(id=product_id).first()
    if not product:
        messages.error(request, "Produit introuvable.")
        return redirect("products")

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            bump_data_version()
            messages.success(request, "Produit modifie avec succes.")
            return redirect("products")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "product_edit.html",
        {
            "active_page": active_page,
            "form": form,
            "product": product,
        },
    )





def lots(request):
    active_page = "lots"

    # -------------------------
    # Pré-remplissage du produit (?product=ID)
    # -------------------------
    initial = {}
    product_id = request.GET.get("product")
    if product_id:
        initial["produit"] = product_id

    # -------------------------
    # Form handling (POST / GET)
    # -------------------------
    if request.method == "POST":
        form = LotForm(request.POST)
        if form.is_valid():
            form.save()
            bump_data_version()
            return redirect("lots")
    else:
        form = LotForm(initial=initial)

    # -------------------------
    # Lots FEFO + expiration logic
    # -------------------------
    lots_qs = (
        Lot.objects
        .select_related("produit", "produit__famille")
        .order_by("date_fin")  # FEFO
    )

    today = date.today()
    items = []

    for lot in lots_qs:
        days_left = (lot.date_fin - today).days
        alert_days = lot.produit.nbr_days_alert

        # Expiration status
        if days_left < 0:
            level = "danger"
            label = "Expiré"
        elif days_left == 0:
            level = "danger"
            label = "Il expire aujourd'hui"
        elif days_left <= alert_days:
            level = "near"
            label = f"Il reste {days_left} jour(s)"
        else:
            level = "ok"
            label = f"Il reste {days_left} jour(s)"

        items.append({
            "produit": lot.produit,
            "date_entree": lot.date_entree,
            "date_fin": lot.date_fin,
            "quantite": lot.quantite,
            "level": level,
            "label": label,
        })

    # -------------------------
    # Lookup JS (barcode / preview)
    # -------------------------
    product_lookup_map = [
        {
            "id": p.id,
            "nom": p.nom or "",
            "reference": p.reference,
            "barcode": p.barcode,
        }
        for p in Produit.objects.all()
    ]

    return render(
        request,
        "lots.html",
        {
            "active_page": active_page,
            "form": form,
            "lots": items,              # ⚠️ items, pas queryset brut
            "product_lookup_map": product_lookup_map,
        }
    )


def movements(request):
    active_page = "movements"
    today = date.today()

    if request.method == "POST":
        form = MovementForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            quantite_demandee = form.cleaned_data["quantite"]

            produit = (
                Produit.objects
                .filter(Q(reference__iexact=code) | Q(barcode__iexact=code))
                .first()
            )

            if not produit:
                messages.error(request, "Produit non disponible.")
                return redirect("movements")

            with transaction.atomic():
                lots = list(
                    Lot.objects
                    .select_for_update()
                    .filter(produit=produit, quantite__gt=0, date_fin__gte=today)
                    .order_by("date_fin")
                )

                stock_disponible = sum(lot.quantite for lot in lots)
                if stock_disponible < quantite_demandee:
                    messages.error(request, "Produit non disponible (quantite insuffisante).")
                    return redirect("movements")

                reste = quantite_demandee
                for lot in lots:
                    if reste == 0:
                        break
                    preleve = min(lot.quantite, reste)
                    lot.quantite -= preleve
                    lot.save(update_fields=["quantite"])
                    reste -= preleve

                Sort.objects.create(produit=produit, quantite=quantite_demandee)
                bump_data_version()
                messages.success(
                    request,
                    f"Sortie enregistree: {produit.reference} (-{quantite_demandee})."
                )
                return redirect("movements")
    else:
        form = MovementForm(initial={"quantite": 1})

    fefo_lots = (
        Lot.objects
        .select_related("produit")
        .filter(quantite__gt=0, date_fin__gte=today)
        .order_by("date_fin")
    )[:10]
    sort_history = (
        Sort.objects
        .select_related("produit")
        .order_by("-date_sortie", "-id")
    )[:10]

    return render(
        request,
        "movements.html",
        {
            "active_page": active_page,
            "form": form,
            "fefo_lots": fefo_lots,
            "sort_history": sort_history,
        },
    )

def alerts(request):
    active_page = "alerts"
    today = date.today()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "delete_expired_lot":
            lot_id = request.POST.get("lot_id")
            lot = Lot.objects.select_related("produit").filter(id=lot_id).first()

            if not lot:
                messages.error(request, "Lot introuvable.")
                return redirect("alerts")

            if lot.date_fin >= today:
                messages.warning(request, "Seuls les lots expires peuvent etre supprimes.")
                return redirect("alerts")

            ref = lot.produit.reference
            lot.delete()
            bump_data_version()
            messages.success(request, f"Lot expire supprime pour le produit {ref}.")
            return redirect("alerts")

    query = (request.GET.get("q") or "").strip()
    famille_filter = (request.GET.get("famille") or "").strip()
    alert_kind = (request.GET.get("kind") or "all").strip().lower()
    sort_by = (request.GET.get("sort") or "").strip().lower()
    valid_kinds = {"all", "stock", "expiry"}
    valid_sorts = {"", "name", "barcode", "date", "days"}
    if alert_kind not in valid_kinds:
        alert_kind = "all"
    if sort_by not in valid_sorts:
        sort_by = ""

    produits_qs = (
        Produit.objects
        .select_related("famille")
        .annotate(stock_total=Sum("lots__quantite"))
    )

    if query:
        query_lower = query.lower()
        produits_qs = [
            p for p in produits_qs
            if (
                query_lower in (p.nom or "").lower()
                or query_lower in (p.reference or "").lower()
                or query_lower in (p.barcode or "").lower()
            )
        ]
    else:
        produits_qs = list(produits_qs)

    if famille_filter:
        produits_qs = [p for p in produits_qs if str(p.famille_id) == famille_filter]

    critical_alerts = []
    warning_alerts = []

    for p in produits_qs:
        stock_total = p.stock_total or 0

        if alert_kind in {"all", "stock"}:
            stock_label = None
            stock_level = None
            if stock_total <= 0:
                stock_level = "danger"
                stock_label = "Rupture de stock"
            elif stock_total <= p.nbr_qnt_alert:
                stock_level = "near"
                stock_label = "Seuil de stock atteint"

            if stock_level:
                next_lot = p.lots.filter(quantite__gt=0).order_by("date_fin").first()
                if next_lot:
                    stock_days_left = (next_lot.date_fin - today).days
                    stock_lot_quantite = next_lot.quantite
                    stock_date_entree = next_lot.date_entree
                    stock_date_fin = next_lot.date_fin
                else:
                    stock_days_left = "-"
                    stock_lot_quantite = "-"
                    stock_date_entree = "-"
                    stock_date_fin = "-"

                row = {
                    "type": "stock",
                    "type_label": "Alerte stock",
                    "status_label": stock_label,
                    "status_level": stock_level,
                    "lot_id": None,
                    "produit_id": p.id,
                    "produit_nom": p.nom,
                    "reference": p.reference,
                    "barcode": p.barcode,
                    "famille": p.famille.nom,
                    "stock_total": stock_total,
                    "lot_quantite": stock_lot_quantite,
                    "date_entree": stock_date_entree,
                    "date_fin": stock_date_fin,
                    "days_left": stock_days_left,
                    "min_qte": p.nbr_qnt_alert,
                    "min_jour": p.nbr_days_alert,
                }
                if stock_level == "danger":
                    critical_alerts.append(row)
                else:
                    warning_alerts.append(row)

        if alert_kind in {"all", "expiry"} and stock_total > 0:
            product_lots = list(
                p.lots.filter(quantite__gt=0).order_by("date_fin")
            )
            for lot in product_lots:
                days_left = (lot.date_fin - today).days

                if days_left < 0:
                    level = "danger"
                    label = "Expire"
                elif days_left == 0:
                    level = "danger"
                    label = "Expire aujourd'hui"
                elif days_left <= p.nbr_days_alert:
                    level = "near"
                    label = "Proche expiration"
                else:
                    continue

                row = {
                    "type": "expiry",
                    "type_label": "Alerte expiration",
                    "status_label": label,
                    "status_level": level,
                    "lot_id": lot.id,
                    "produit_id": p.id,
                    "produit_nom": p.nom,
                    "reference": p.reference,
                    "barcode": p.barcode,
                    "famille": p.famille.nom,
                    "stock_total": stock_total,
                    "lot_quantite": lot.quantite,
                    "date_entree": lot.date_entree,
                    "date_fin": lot.date_fin,
                    "days_left": days_left,
                    "min_qte": p.nbr_qnt_alert,
                    "min_jour": p.nbr_days_alert,
                }

                if level == "danger":
                    critical_alerts.append(row)
                else:
                    warning_alerts.append(row)

    if sort_by == "name":
        critical_alerts.sort(key=lambda item: (item.get("produit_nom") or "").lower())
        warning_alerts.sort(key=lambda item: (item.get("produit_nom") or "").lower())
    elif sort_by == "barcode":
        critical_alerts.sort(key=lambda item: (item.get("barcode") or "").lower())
        warning_alerts.sort(key=lambda item: (item.get("barcode") or "").lower())
    elif sort_by == "date":
        critical_alerts.sort(
            key=lambda item: (
                item.get("date_fin") == "-",
                item.get("date_fin") if item.get("date_fin") != "-" else date.max,
            )
        )
        warning_alerts.sort(
            key=lambda item: (
                item.get("date_fin") == "-",
                item.get("date_fin") if item.get("date_fin") != "-" else date.max,
            )
        )
    elif sort_by == "days":
        critical_alerts.sort(
            key=lambda item: (
                not isinstance(item.get("days_left"), int),
                item.get("days_left") if isinstance(item.get("days_left"), int) else 999999,
            )
        )
        warning_alerts.sort(
            key=lambda item: (
                not isinstance(item.get("days_left"), int),
                item.get("days_left") if isinstance(item.get("days_left"), int) else 999999,
            )
        )

    familles = Famille.objects.all().order_by("nom")
    context = {
        "active_page": active_page,
        "critical_alerts": critical_alerts,
        "warning_alerts": warning_alerts,
        "familles": familles,
        "query": query,
        "famille_filter": famille_filter,
        "kind_filter": alert_kind,
        "sort_filter": sort_by,
    }
    return render(request, "alerts.html", context)

def historique(request):
    active_page="historique"
    return render(request, "historique.html",{"active_page":active_page})

def famille(request):
    active_page = "famille"
    form = FamilleForm()

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "add_famille":
            form = FamilleForm(request.POST)
            if form.is_valid():
                form.save()
                bump_data_version()
                return redirect("famille")

        elif action == "delete_famille":
            famille_id = request.POST.get("famille_id")
            delete_mode = request.POST.get("delete_mode", "family_only")

            fam = Famille.objects.filter(id=famille_id).first()
            if not fam:
                messages.error(request, "Famille introuvable.")
                return redirect("famille")

            if delete_mode == "with_products":
                deleted_products = fam.produits.count()
                fam.produits.all().delete()
                fam_name = fam.nom
                fam.delete()
                bump_data_version()
                messages.success(
                    request,
                    f"Famille '{fam_name}' supprimee avec {deleted_products} produit(s).",
                )
                return redirect("famille")

            # Default behavior: move linked products to fallback family "-"
            fallback_famille, _ = Famille.objects.get_or_create(nom="-")
            if fam.id == fallback_famille.id:
                messages.warning(
                    request,
                    "La famille par defaut '-' ne peut pas etre supprimee.",
                )
                return redirect("famille")

            moved_count = fam.produits.count()
            fam.produits.update(famille=fallback_famille)
            fam_name = fam.nom
            fam.delete()
            bump_data_version()
            messages.success(
                request,
                f"Famille '{fam_name}' supprimee. {moved_count} produit(s) deplaces vers '-'.",
            )
            return redirect("famille")

        elif action == "edit_famille":
            famille_id = request.POST.get("famille_id")
            new_name = (request.POST.get("nom") or "").strip()

            fam = Famille.objects.filter(id=famille_id).first()
            if not fam:
                messages.error(request, "Famille introuvable.")
                return redirect("famille")

            if not new_name:
                messages.warning(request, "Le nom de la famille est obligatoire.")
                return redirect("famille")

            exists = Famille.objects.filter(nom__iexact=new_name).exclude(id=fam.id).exists()
            if exists:
                messages.warning(request, "Ce nom de famille existe deja.")
                return redirect("famille")

            old_name = fam.nom
            fam.nom = new_name
            fam.save(update_fields=["nom"])
            bump_data_version()
            messages.success(request, f"Famille modifiee: '{old_name}' -> '{new_name}'.")
            return redirect("famille")

    familles = Famille.objects.all().order_by("nom")
    return render(
        request,
        "famille.html",
        {
            "active_page": active_page,
            "familles": familles,
            "form": form,
        },
    )
