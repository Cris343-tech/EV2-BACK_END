import decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comida', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comida',
            name='precio',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[MinValueValidator(decimal.Decimal('0'))],
            ),
        ),
    ]
