from django.urls import path
from .views import (
    PautaGerarView,
    PautaCompletaView,
    PautaPDFView,
    PautaXLSXView,
    PautaDOCXView,
    PautaExportJSONView,
    PautasEstatisticasGeraisView
)

urlpatterns = [
    path('gerar', PautaGerarView.as_view(), name='pauta_gerar_no_slash'),
    path('gerar/', PautaGerarView.as_view(), name='pauta_gerar'),
    path('turma/<uuid:turma_id>/completa', PautaCompletaView.as_view(), name='pauta_completa_no_slash'),
    path('turma/<uuid:turma_id>/completa/', PautaCompletaView.as_view(), name='pauta_completa'),
    path('turma/<uuid:turma_id>/pdf', PautaPDFView.as_view(), name='pauta_pdf_no_slash'),
    path('turma/<uuid:turma_id>/pdf/', PautaPDFView.as_view(), name='pauta_pdf'),
    path('turma/<uuid:turma_id>/export-xlsx', PautaXLSXView.as_view(), name='pauta_xlsx_no_slash'),
    path('turma/<uuid:turma_id>/export-xlsx/', PautaXLSXView.as_view(), name='pauta_xlsx'),
    path('turma/<uuid:turma_id>/docx', PautaDOCXView.as_view(), name='pauta_docx_no_slash'),
    path('turma/<uuid:turma_id>/docx/', PautaDOCXView.as_view(), name='pauta_docx'),
    path('turma/<uuid:turma_id>/export-json', PautaExportJSONView.as_view(), name='pauta_json_no_slash'),
    path('turma/<uuid:turma_id>/export-json/', PautaExportJSONView.as_view(), name='pauta_json'),
    # Acta de Conselho aliases
    path('turma/<uuid:turma_id>/acta', PautaCompletaView.as_view(), name='acta_data_no_slash'),
    path('turma/<uuid:turma_id>/acta/', PautaCompletaView.as_view(), name='acta_data'),
    path('turma/<uuid:turma_id>/acta-pdf', PautaPDFView.as_view(), name='acta_pdf_no_slash'),
    path('turma/<uuid:turma_id>/acta-pdf/', PautaPDFView.as_view(), name='acta_pdf'),
    path('turma/<uuid:turma_id>/acta-docx', PautaDOCXView.as_view(), name='acta_docx_no_slash'),
    path('turma/<uuid:turma_id>/acta-docx/', PautaDOCXView.as_view(), name='acta_docx'),
    path('turma/<uuid:turma_id>/acta-xlsx', PautaXLSXView.as_view(), name='acta_xlsx_no_slash'),
    path('turma/<uuid:turma_id>/acta-xlsx/', PautaXLSXView.as_view(), name='acta_xlsx'),
    path('turma/<uuid:turma_id>/acta-json', PautaExportJSONView.as_view(), name='acta_json_no_slash'),
    path('turma/<uuid:turma_id>/acta-json/', PautaExportJSONView.as_view(), name='acta_json'),
    path('estatisticas-gerais', PautasEstatisticasGeraisView.as_view(), name='pautas_estatisticas_no_slash'),
    path('estatisticas-gerais/', PautasEstatisticasGeraisView.as_view(), name='pautas_estatisticas'),
    path('estatisticas-gerais/xlsx', PautaXLSXView.as_view(), name='pautas_estatisticas_xlsx_no_slash'),
    path('estatisticas-gerais/xlsx/', PautaXLSXView.as_view(), name='pautas_estatisticas_xlsx'),
]
