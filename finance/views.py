from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import User, OTP
from django.db import IntegrityError
import random

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
            if user.last_login < timezone.now() - timedelta(days=5):
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
            return redirect('dashboard')
        else:
            return render(request, 'auth/otp.html', {'error': 'Le code OTP est incorrect'})

    return render(request, 'auth/otp.html')


# ---------------- Dashboard ----------------
def dashboardpage(request):
    return render(request, 'pages/dashboard.html',{'user':request.user})


# ---------------- Profil ----------------
def profilpage(request):
    return render(request, 'pages/profil.html')
