# Generated manually to make question field required

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_alter_passageannotation_options_and_more'),
    ]

    operations = [
        # First, delete any annotations without a question (should be 0, but safe)
        migrations.RunSQL(
            "DELETE FROM passage_annotations WHERE question_id IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Now make the field non-nullable
        migrations.AlterField(
            model_name='passageannotation',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to='api.question'),
        ),
    ]
