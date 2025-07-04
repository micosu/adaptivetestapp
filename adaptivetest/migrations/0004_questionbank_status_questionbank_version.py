# Generated by Django 5.2.3 on 2025-06-26 21:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adaptivetest', '0003_questionbank_antonym_questionbank_unrelated'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionbank',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('retired', 'Retired'), ('draft', 'Draft')], default='active', max_length=10),
        ),
        migrations.AddField(
            model_name='questionbank',
            name='version',
            field=models.CharField(blank=True, max_length=15),
        ),
    ]
