from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import User, OTP,Compte,Transaction
from django.db.models import Sum, F, Q
from django.db.models.functions import TruncMonth
from django.db import IntegrityError
import random
from decimal import Decimal
#
# PDF
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import io
from datetime import datetime

#


from django.core.mail import send_mail
from django.conf import settings

# ---------------- Home ----------------
def home(request):
    return render(request, 'landing/index.html')


# ---------------- Register ----------------

def register(request):
    if request.method == 'POST':
        print("POST DATA =", request.POST) # A supprimer après 

        nom_complet = request.POST.get('nom_complet')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        # Vérification champs obligatoires
        if not all([nom_complet, email, password, password2]):
            return render(request, 'auth/register.html', {
                'error': 'Tous les champs sont obligatoires'
            })

        # Vérification mots de passe
        if password != password2:
            return render(request, 'auth/register.html', {
                'error': 'Les mots de passe ne correspondent pas'
            })

        # Vérification email existant
        if User.objects.filter(email=email).exists():
            return render(request, 'auth/register.html', {
                'error': "L'email existe déjà"
            })

        try:
            # Création utilisateur
            user = User(
                nom_complet=nom_complet,
                email=email,
                identifiant=str(random.randint(10000000, 99999999))
            )
            user.set_password(password)
            user.save()

            # Génération OTP
            otp_code = ''.join(str(random.randint(0, 9)) for _ in range(6))
            OTP.objects.create(user=user, otp=otp_code)

            # 🔹 ENVOI EMAIL OTP
            send_mail(
                subject='Code de vérification OTP',
                message=f'Bonjour {nom_complet},\n\nVotre code OTP est : {otp_code}\n\nCe code est confidentiel.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )

            # Message succès
            messages.success(
                request,
                "Inscription réussie. Un code OTP a été envoyé à votre adresse email."
            )

            # Session OTP
            request.session['user_id'] = user.id

            return redirect('otp')

        except IntegrityError as e:
            print("ERREUR BD :", e)
            return render(request, 'auth/register.html', {
                'error': "Erreur lors de l'inscription. Réessayez."
            })

        except Exception as e:
            print("ERREUR EMAIL / AUTRE :", e)
            return render(request, 'auth/register.html', {
                'error': "Impossible d'envoyer le code OTP. Vérifiez l'email."
            })

    return render(request, 'auth/register.html')



# ---------------- Login ----------------
def login(request):
    if request.method == 'POST':
        identifiant = request.POST.get('identifiant')  # email ou identifiant
        password = request.POST.get('password')

        # Authentification par email ou identifiant
        try:
            user = User.objects.get(email=identifiant)
        except User.DoesNotExist:
            try:
                user = User.objects.get(identifiant=identifiant)
            except User.DoesNotExist:
                user = None

        if user is not None and user.check_password(password):
            auth_login(request, user)

            # Vérifier dernière connexion
            if user.last_login < timezone.now() - timedelta(days=1):
                otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                OTP.objects.create(user=user, otp=otp_code)
                request.session['user_id'] = user.id
                return redirect('otp')

            return redirect('dashboard')
        else:
            return render(request, 'auth/login.html', {'error': 'Identifiant ou mot de passe incorrect'})

    return render(request, 'auth/login.html')


#------deconnexion -----

def logout(request):
    auth_logout(request)
    messages.success(request, "vous êtes deconnecté(e)s)")
    print ("deconnecter avec succès")
    return redirect('login')
# ---------------- OTP ----------------
def otp(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        otp_input = request.POST.get('otp')

        # Vérifier OTP valide pour cet utilisateur
        if OTP.objects.filter(user=user, otp=otp_input).exists():
            OTP.objects.filter(user=user).delete()  # supprimer OTP après usage
            return redirect('login')
        else:
            return render(request, 'auth/otp.html', {'error': 'Le code OTP est incorrect'})

    return render(request, 'auth/otp.html')


# ---------------- Dashboard ----------------
def dashboardpage(request):
    # Récupère tous les comptes de l'utilisateur connecté
    comptes = Compte.objects.filter(compte_user=request.user)
    
    # Booléen pour savoir si l'utilisateur a au moins un compte
    has_compte = comptes.exists()
    # Calculs globaux
    total_solde = sum(c.solde for c in comptes)
    total_revenus = sum(c.total_revenus for c in comptes)
    total_depenses = sum(c.total_depenses for c in comptes)

    # afficher les transaction
        # Transactions liées aux comptes de l'utilisateur
    transactions = Transaction.objects.filter(compte__in=comptes).order_by('-date')[:5]

    # Contexte pour le template
    context = {
        'user': request.user,
        'comptes': comptes,
        'has_compte': has_compte,
        'transactions':transactions,
        'total_solde':total_solde,
        'total_revenus':total_revenus,
        'total_depenses':total_depenses
    }
    
    return render(request, 'pages/dashboard.html', context)


# ---------------- Profil ----------------
def profilpage(request):
    return render(request, 'pages/profil.html',{'user':request.user})


 #----partie creation de compte---


@login_required


def creation_compte(request):
    if request.method == "POST":
        print("POST DATA =", request.POST) # A supprimer après 

        nom_compte = request.POST.get("nom_compte")
        description = request.POST.get("description")

        if not nom_compte:
            messages.error(request, "Le nom du compte est obligatoire.")
            return redirect('dashboard')

        Compte.objects.create(
            nom_compte=nom_compte,
            description=description,
            compte_user = request.user

        )

        messages.success(request, f"Le compte '{nom_compte}' a été créé.")
        return redirect('dashboard')

    return redirect('dashboard')


@login_required
def ajouter_revenu(request):
    if request.method == "POST":
        compte_id = request.POST.get("compte")
        montant = Decimal(request.POST.get("montant"))
        description = request.POST.get("description")

        compte = get_object_or_404(Compte, id=compte_id, compte_user=request.user)

        # Création de la transaction revenu
        Transaction.objects.create(
            type='REVENU',
            montant=montant,
            description=description,
            compte=compte
        )

        messages.success(request, f"Revenu de {montant} FCFA ajouté au compte {compte.nom_compte}.")
        return redirect('dashboard')

    return redirect('dashboard')


@login_required
def enregistrer_depense(request):
    if request.method == "POST":
        compte_id = request.POST.get("compte")
        montant = Decimal(request.POST.get("montant"))
        description = request.POST.get("description")

        compte = get_object_or_404(Compte, id=compte_id, compte_user=request.user)

        # Vérifier si le solde est suffisant
        if montant > compte.solde:
            messages.error(request, "Solde insuffisant pour cette dépense.")
            return redirect('dashboard')

        # Création de la transaction dépense
        Transaction.objects.create(
            type='DEPENSE',
            montant=montant,
            description=description,
            compte=compte
        )

        messages.success(request, f"Dépense de {montant} FCFA enregistrée pour le compte {compte.nom_compte}.")
        return redirect('dashboard')

    return redirect('dashboard')    



@login_required
def compte_list(request):
    q = request.GET.get('q', '').strip()

    comptes = Compte.objects.filter(compte_user=request.user)

    if q:
        comptes = comptes.filter(nom_compte__icontains=q)

    context = {
        'comptes': comptes,
        'query': q,
    }

    return render(request, 'pages/compte.html', context)

@login_required
def compte_delete(request, compte_id):
    compte = get_object_or_404(
        Compte,
        id=compte_id,
        compte_user=request.user
    )

    if request.method == "POST":
        compte.delete()
        return redirect('compte_list')

    return redirect('compte_list')


@login_required
def compte_update(request, compte_id):
    compte = get_object_or_404(Compte, id=compte_id, compte_user=request.user)
    if request.method == "POST":
        compte.nom_compte = request.POST.get('nom_compte')
        compte.description = request.POST.get('description')
        compte.save()
        return redirect('compte_list') 


@login_required
def transaction_page(request):
    comptes = Compte.objects.filter(compte_user=request.user)
    total_solde = sum(c.solde for c in comptes)
    compte_id = request.GET.get('compte')
    search_query = request.GET.get('q')

    # Toutes les transactions de tous les comptes de l'utilisateur
    transactions = Transaction.objects.filter(compte__in=comptes)

    # Filtrer par compte si sélectionné (optionnel)
    if compte_id:
        transactions = transactions.filter(compte_id=compte_id)
    if search_query:
        transactions = transactions.filter(description__icontains=search_query)

    transactions = transactions.order_by('-date')

    # Pour l'en-tête : compte sélectionné ou "Tous les comptes"
    compte_actif = None
    if compte_id:
        try:
            compte_actif = comptes.get(id=compte_id)
        except Compte.DoesNotExist:
            pass
    solde = compte_actif.solde if compte_actif else total_solde

    context = {
        'transactions': transactions,
        'comptes': comptes,
        'compte_actif': compte_actif,
        'solde': solde,
        'total_solde': total_solde,
        'selected_compte': compte_id,
        'search_query': search_query,
        'transactions_json': list(transactions.values('id', 'description', 'montant', 'date', 'type')),
    }
    return render(request, 'pages/transaction.html', context)

#partie rapport

@login_required
def report_page(request):
    comptes = Compte.objects.filter(compte_user=request.user)
    transactions = Transaction.objects.filter(compte__in=comptes).order_by('-date')

    # --- 1. Graphique Camembert : répartition des dépenses par compte (pas de champ categorie) ---
    depenses = transactions.filter(type='DEPENSE')
    by_compte = depenses.values('compte__nom_compte').annotate(total=Sum('montant')).order_by('-total')
    labels_categories = [item['compte__nom_compte'] or 'Sans compte' for item in by_compte]
    data_categories = [float(item['total']) for item in by_compte]

    # --- 2. Graphique Barres : évolution mensuelle (revenus vs dépenses par type) ---
    monthly_data = transactions.annotate(month=TruncMonth('date')).values('month').annotate(
        income=Sum('montant', filter=Q(type='REVENU')),
        expense=Sum('montant', filter=Q(type='DEPENSE'))
    ).order_by('month')
    labels_months = [item['month'].strftime('%b %Y') for item in monthly_data]
    data_income = [float(item['income'] or 0) for item in monthly_data]
    data_expense = [float(item['expense'] or 0) for item in monthly_data]

    # --- 3. Totaux globaux ---
    agg = transactions.aggregate(
        total_revenu=Sum('montant', filter=Q(type='REVENU')),
        total_depense=Sum('montant', filter=Q(type='DEPENSE'))
    )
    total_revenu = agg['total_revenu'] or 0
    total_depense = agg['total_depense'] or 0
    solde_net = total_revenu - total_depense

    context = {
        'labels_categories': labels_categories,
        'data_categories': data_categories,
        'labels_months': labels_months,
        'data_income': data_income,
        'data_expense': data_expense,
        'total_revenu': total_revenu,
        'total_depense': total_depense,
        'solde_net': solde_net,
        'transactions': transactions,
        'comptes':comptes,
    }
    return render(request, 'pages/rapport.html', context)


# fonction de téléchargement 
@login_required
def export_pdf(request):
    if request.method == "POST":

        selected_comptes = request.POST.getlist("comptes")

        # Sécurité multi-tenant
        if "all" in selected_comptes:
            comptes = Compte.objects.filter(compte_user=request.user)
        else:
            comptes = Compte.objects.filter(
                id__in=selected_comptes,
                compte_user=request.user
            )

        transactions = Transaction.objects.filter(
            compte__in=comptes
        ).order_by("-date")

        # Création buffer mémoire
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4
        )

        elements = []
        styles = getSampleStyleSheet()

        # ---- Titre ----
        elements.append(Paragraph("WALLETIS - RAPPORT FINANCIER", styles['Title']))
        elements.append(Spacer(1, 0.3 * inch))

        elements.append(
            Paragraph(
                f"Utilisateur : {request.user.nom_complet}",
                styles['Normal']
            )
        )

        elements.append(
            Paragraph(
                f"Généré le : {datetime.now().strftime('%d/%m/%Y')}",
                styles['Normal']
            )
        )

        elements.append(Spacer(1, 0.3 * inch))

        # ---- Tableau ----
        data = [["Date", "Compte", "Description", "Type", "Montant (FCFA)"]]

        total_revenu = Decimal("0")
        total_depense = Decimal("0")

        for t in transactions:

            if t.type == "REVENU":
                total_revenu += t.montant
            else:
                total_depense += t.montant

            data.append([
                t.date.strftime("%d/%m/%Y"),
                t.compte.nom_compte,
                t.description or "",
                t.type,
                f"{t.montant:.2f}"
            ])

        table = Table(data, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.4 * inch))

        # ---- Résumé financier ----
        solde_net = total_revenu - total_depense

        elements.append(Paragraph("RÉSUMÉ FINANCIER", styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))

        summary_data = [
            ["Total Revenus", f"{total_revenu:.2f} FCFA"],
            ["Total Dépenses", f"{total_depense:.2f} FCFA"],
            ["Solde Net", f"{solde_net:.2f} FCFA"],
        ]

        summary_table = Table(summary_data, colWidths=[250, 150])
        summary_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ]))

        elements.append(summary_table)

        # Construction PDF
        doc.build(elements)

        buffer.seek(0)

        response = HttpResponse(
            buffer,
            content_type='application/pdf'
        )

        response['Content-Disposition'] = (
            f'attachment; filename="walletis_rapport_{datetime.now().strftime("%Y%m%d")}.pdf"'
        )

        return response

    return redirect("dashboard")
    