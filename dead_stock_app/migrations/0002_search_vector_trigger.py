from django.db import migrations

CREATE_TRIGGER = """
CREATE TRIGGER inventoryitem_search_vector_update
BEFORE INSERT OR UPDATE ON dead_stock_app_inventoryitem
FOR EACH ROW EXECUTE FUNCTION
  tsvector_update_trigger(search_vector, 'pg_catalog.simple', name, description);
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS inventoryitem_search_vector_update ON dead_stock_app_inventoryitem;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("dead_stock_app", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_TRIGGER,
            reverse_sql=DROP_TRIGGER,
        ),
    ]
