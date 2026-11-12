from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="webhook_url",
            field=models.URLField(
                blank=True,
                help_text="Optional URL that receives a POST for pending invoice reminders.",
            ),
        ),
    ]
