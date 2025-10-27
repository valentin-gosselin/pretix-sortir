# Generated migration for encrypting API token field

from django.db import migrations
import pretix_sortir.fields


class Migration(migrations.Migration):

    dependencies = [
        ('pretix_sortir', '0006_add_api_url_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sortirorganizersettings',
            name='api_token',
            field=pretix_sortir.fields.EncryptedTextField(
                blank=True,
                help_text='Token d\'authentification fourni par l\'APRAS (chiffré au repos)',
                verbose_name='Token API'
            ),
        ),
    ]
