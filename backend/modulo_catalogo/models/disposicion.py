from django.db import models


class DisposicionNormativa(models.Model):
    documento = models.ForeignKey('DocumentoNorma', on_delete=models.PROTECT, related_name='disposiciones')
    numero = models.CharField(max_length=80)
    tipo = models.CharField(max_length=30, choices=[('final', 'Final'), ('derogatoria', 'Derogatoria'), ('abrogatoria', 'Abrogatoria')])
    titulo = models.CharField(max_length=500, blank=True)
    contenido = models.TextField()

    class Meta:
        db_table = 'disposiciones_normativas'
        ordering = ['documento_id', 'id']
        constraints = [models.UniqueConstraint(fields=['documento', 'numero'], name='disposicion_documento_unica')]
