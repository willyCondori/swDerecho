from rest_framework import serializers

from modulo_ia.models.jurisprudencia import ResultadoJurisprudencia


class ResultadoJurisprudenciaSerializer(serializers.ModelSerializer):
    registro_id = serializers.IntegerField(source="resolucion_id", read_only=True)
    fuente_id = serializers.CharField(source="resolucion.fuente_id", read_only=True)
    numero = serializers.CharField(source="resolucion.numero", read_only=True)
    expediente = serializers.CharField(source="resolucion.expediente", read_only=True)
    fecha = serializers.DateField(source="resolucion.fecha", read_only=True)
    materia = serializers.CharField(source="resolucion.materia", read_only=True)
    sala = serializers.CharField(source="resolucion.sala", read_only=True)
    url_fuente = serializers.CharField(source="resolucion.url_fuente", read_only=True)
    url_pdf = serializers.CharField(source="resolucion.url_pdf", read_only=True)
    desactualizada = serializers.SerializerMethodField()

    def get_desactualizada(self, obj):
        return not obj.resolucion.activa or obj.huella_fuente != obj.resolucion.huella

    class Meta:
        model = ResultadoJurisprudencia
        fields = ["id", "registro_id", "fuente_id", "numero", "expediente", "fecha", "materia", "sala",
                  "url_fuente", "url_pdf", "posicion", "score_semantico", "fragmento",
                  "modelo_version", "desactualizada"]
        read_only_fields = fields
