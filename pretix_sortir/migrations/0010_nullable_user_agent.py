# Generated manually to fix user_agent nullable

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0009_add_audit_log'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sortirauditlog',
            name='user_agent',
            field=models.TextField(blank=True, null=True, verbose_name='User Agent'),
        ),
    ]
