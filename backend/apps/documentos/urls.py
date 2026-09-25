from django.urls import path
from .views import (
    BoletimView,
    BoletimPDFView,
    DeclaracaoView,
    DeclaracaoPDFView,
    CertificadoImpressaoView,
    ReciboImpressaoView,
    FichaAlunoView
)

urlpatterns = [
    # Boletim
    path('boletim/<uuid:aluno_id>', BoletimView.as_view(), name='impressao_boletim_no_slash'),
    path('boletim/<uuid:aluno_id>/', BoletimView.as_view(), name='impressao_boletim'),
    path('boletim/<uuid:aluno_id>/pdf', BoletimPDFView.as_view(), name='impressao_boletim_pdf_no_slash'),
    path('boletim/<uuid:aluno_id>/pdf/', BoletimPDFView.as_view(), name='impressao_boletim_pdf'),
    path('boletim/<uuid:aluno_id>/docx', BoletimPDFView.as_view(), name='impressao_boletim_docx_no_slash'),
    path('boletim/<uuid:aluno_id>/docx/', BoletimPDFView.as_view(), name='impressao_boletim_docx'),
    path('boletim/<uuid:aluno_id>/xlsx', BoletimPDFView.as_view(), name='impressao_boletim_xlsx_no_slash'),
    path('boletim/<uuid:aluno_id>/xlsx/', BoletimPDFView.as_view(), name='impressao_boletim_xlsx'),
    path('boletim/<uuid:aluno_id>/json', BoletimView.as_view(), name='impressao_boletim_json_no_slash'),
    path('boletim/<uuid:aluno_id>/json/', BoletimView.as_view(), name='impressao_boletim_json'),

    # Declaração
    path('declaracao/<uuid:aluno_id>', DeclaracaoView.as_view(), name='impressao_declaracao_no_slash'),
    path('declaracao/<uuid:aluno_id>/', DeclaracaoView.as_view(), name='impressao_declaracao'),
    path('declaracao/<uuid:aluno_id>/pdf', DeclaracaoPDFView.as_view(), name='impressao_declaracao_pdf_no_slash'),
    path('declaracao/<uuid:aluno_id>/pdf/', DeclaracaoPDFView.as_view(), name='impressao_declaracao_pdf'),
    path('declaracao/<uuid:aluno_id>/docx', DeclaracaoPDFView.as_view(), name='impressao_declaracao_docx_no_slash'),
    path('declaracao/<uuid:aluno_id>/docx/', DeclaracaoPDFView.as_view(), name='impressao_declaracao_docx'),
    path('declaracao/<uuid:aluno_id>/xlsx', DeclaracaoPDFView.as_view(), name='impressao_declaracao_xlsx_no_slash'),
    path('declaracao/<uuid:aluno_id>/xlsx/', DeclaracaoPDFView.as_view(), name='impressao_declaracao_xlsx'),
    path('declaracao/<uuid:aluno_id>/json', DeclaracaoView.as_view(), name='impressao_declaracao_json_no_slash'),
    path('declaracao/<uuid:aluno_id>/json/', DeclaracaoView.as_view(), name='impressao_declaracao_json'),

    # Certificado
    path('certificado/<uuid:aluno_id>', CertificadoImpressaoView.as_view(), name='impressao_cert_no_slash'),
    path('certificado/<uuid:aluno_id>/', CertificadoImpressaoView.as_view(), name='impressao_cert'),
    path('certificado/<uuid:aluno_id>/pdf', DeclaracaoPDFView.as_view(), name='impressao_cert_pdf_no_slash'),
    path('certificado/<uuid:aluno_id>/pdf/', DeclaracaoPDFView.as_view(), name='impressao_cert_pdf'),

    # Recibo
    path('recibo/<uuid:pagamento_id>', ReciboImpressaoView.as_view(), name='impressao_recibo_no_slash'),
    path('recibo/<uuid:pagamento_id>/', ReciboImpressaoView.as_view(), name='impressao_recibo'),
    path('recibo/<uuid:pagamento_id>/pdf', ReciboImpressaoView.as_view(), name='impressao_recibo_pdf_no_slash'),
    path('recibo/<uuid:pagamento_id>/pdf/', ReciboImpressaoView.as_view(), name='impressao_recibo_pdf'),

    # Ficha do Aluno
    path('ficha/<uuid:aluno_id>', FichaAlunoView.as_view(), name='impressao_ficha_no_slash'),
    path('ficha/<uuid:aluno_id>/', FichaAlunoView.as_view(), name='impressao_ficha'),
]
