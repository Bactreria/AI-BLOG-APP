# Generated by Django 4.2.2 on 2024-08-24 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_blog_generator', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='formated_content',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
