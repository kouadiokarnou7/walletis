from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import random
import string
from django.conf import settings

class User(AbstractUser):
    nom_complet = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    identifiant = models.CharField(max_length=10, unique=True)

    # Évite les conflits avec auth.User
    groups = models.ManyToManyField(
        Group,
        related_name='finance_user_set',
        blank=True,
        help_text='Les groupes auxquels appartient l’utilisateur.',
        verbose_name='groupes'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='finance_user_set_perm',
        blank=True,
        help_text='Permissions spécifiques de l’utilisateur.',
        verbose_name='permissions utilisateur'
    )

    def save(self, *args, **kwargs):
        # Générer un username automatique
        if not self.username:
            base = self.nom_complet.lower().replace(" ", "")
            while True:
                suffix = ''.join(random.choices(string.digits, k=2))
                username = f"{base}{suffix}"

                if len(username) < 8:
                    username += ''.join(random.choices(string.digits, k=8-len(username)))

                if not User.objects.filter(username=username).exists():
                    self.username = username
                    break

        # Générer un identifiant unique si pas déjà défini
        if not self.identifiant:
            while True:
                ident = ''.join(random.choices(string.digits, k=8))
                if not User.objects.filter(identifiant=ident).exists():
                    self.identifiant = ident
                    break

        super().save(*args, **kwargs)




class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

