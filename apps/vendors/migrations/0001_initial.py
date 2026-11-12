import apps.vendors.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Vendor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                (
                    "gstin",
                    models.CharField(
                        max_length=15, validators=[apps.vendors.validators.validate_gstin]
                    ),
                ),
                ("state_code", models.CharField(editable=False, max_length=2)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vendors",
                        to="accounts.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organization", "gstin"), name="unique_vendor_gstin"
                    )
                ],
            },
        ),
    ]
