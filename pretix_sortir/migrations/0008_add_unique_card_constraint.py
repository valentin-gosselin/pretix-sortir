# Generated manually for security constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0007_encrypt_api_token'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='sortirusage',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status__in', ['validated', 'used', 'pending'])),
                fields=('event', 'sortir_number_hash'),
                name='unique_card_per_event_active',
                violation_error_message='Cette carte a déjà été utilisée pour cet événement'
            ),
        ),
    ]
