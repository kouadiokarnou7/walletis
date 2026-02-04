from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import User, OTP,Compte,Transaction
from django.db import IntegrityError
import random
from decimal import Decimal


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
    transactions = Transaction.objects.filter(compte__in=comptes).order_by('-date')

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
