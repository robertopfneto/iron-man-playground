from django.db import migrations

CRIAR = """
CREATE VIRTUAL TABLE IF NOT EXISTS conhecimento_secao_fts USING fts5(
    titulos, texto, caminho,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""

REMOVER = "DROP TABLE IF EXISTS conhecimento_secao_fts;"


class Migration(migrations.Migration):
    dependencies = [("conhecimento", "0001_initial")]

    operations = [migrations.RunSQL(CRIAR, REMOVER)]
