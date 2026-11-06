from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fleet", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="imei",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
    ]
