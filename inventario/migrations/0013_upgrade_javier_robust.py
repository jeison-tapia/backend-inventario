from django.db import migrations

def make_javier_admin_robust(apps, schema_editor):
    Usuario = apps.get_model('inventario', 'Usuario')
    usuarios = Usuario.objects.filter(username__icontains='javier')
    for javier in usuarios:
        javier.rol = 'ADMIN'
        javier.is_superuser = True
        javier.is_staff = True
        javier.save()

class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0012_upgrade_javier_to_admin'),
    ]

    operations = [
        migrations.RunPython(make_javier_admin_robust),
    ]
