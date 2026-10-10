from django.urls import path
from .views import (
    BoletimView,
    BoletimPDFView,
    BoletimDOCXView,
    BoletimXLSXView,
    DeclaracaoView,
    DeclaracaoPDFView,
    DeclaracaoDOCXView,
    DeclaracaoXLSXView,
    CertificadoImpressaoView,
    CertificadoPDFView,
    CertificadoDOCXView,
    CertificadoXLSXView,
    LoteImpressaoView,
    LoteXLSXView,
    ReciboImpressaoView,
    ReciboPDFView,
    ReciboDOCXView,
    FichaAlunoView,
    FichaPDFView,
    FichaDOCXView,
)

urlpatterns = [
    # Lote de Impressão (Boletins, Declarações e Certificados da turma inteira)
    path('lote/turma/<uuid:turma_id>', LoteImpressaoView.as_view(), name='impressao_lote_no_slash'),
    path('lote/turma/<uuid:turma_id>/', LoteImpressaoView.as_view(), name='impressao_lote'),
    path('lote/turma/<uuid:turma_id>/xlsx', LoteXLSXView.as_view(), name='impressao_lote_xlsx_no_slash'),
    path('lote/turma/<uuid:turma_id>/xlsx/', LoteXLSXView.as_view(), name='impressao_lote_xlsx'),

    # Boletim
    path('boletim/<uuid:aluno_id>', BoletimView.as_view(), name='impressao_boletim_no_slash'),
    path('boletim/<uuid:aluno_id>/', BoletimView.as_view(), name='impressao_boletim'),
    path('boletim/<uuid:aluno_id>/pdf', BoletimPDFView.as_view(), name='impressao_boletim_pdf_no_slash'),
    path('boletim/<uuid:aluno_id>/pdf/', BoletimPDFView.as_view(), name='impressao_boletim_pdf'),
    path('boletim/<uuid:aluno_id>/docx', BoletimDOCXView.as_view(), name='impressao_boletim_docx_no_slash'),
    path('boletim/<uuid:aluno_id>/docx/', BoletimDOCXView.as_view(), name='impressao_boletim_docx'),
    path('boletim/<uuid:aluno_id>/xlsx', BoletimXLSXView.as_view(), name='impressao_boletim_xlsx_no_slash'),
    path('boletim/<uuid:aluno_id>/xlsx/', BoletimXLSXView.as_view(), name='impressao_boletim_xlsx'),
    path('boletim/<uuid:aluno_id>/json', BoletimView.as_view(), name='impressao_boletim_json_no_slash'),
    path('boletim/<uuid:aluno_id>/json/', BoletimView.as_view(), name='impressao_boletim_json'),

    # Declaração
    path('declaracao/<uuid:aluno_id>', DeclaracaoView.as_view(), name='impressao_declaracao_no_slash'),
    path('declaracao/<uuid:aluno_id>/', DeclaracaoView.as_view(), name='impressao_declaracao'),
    path('declaracao/<uuid:aluno_id>/pdf', DeclaracaoPDFView.as_view(), name='impressao_declaracao_pdf_no_slash'),
    path('declaracao/<uuid:aluno_id>/pdf/', DeclaracaoPDFView.as_view(), name='impressao_declaracao_pdf'),
    path('declaracao/<uuid:aluno_id>/docx', DeclaracaoDOCXView.as_view(), name='impressao_declaracao_docx_no_slash'),
    path('declaracao/<uuid:aluno_id>/docx/', DeclaracaoDOCXView.as_view(), name='impressao_declaracao_docx'),
    path('declaracao/<uuid:aluno_id>/xlsx', DeclaracaoXLSXView.as_view(), name='impressao_declaracao_xlsx_no_slash'),
    path('declaracao/<uuid:aluno_id>/xlsx/', DeclaracaoXLSXView.as_view(), name='impressao_declaracao_xlsx'),
    path('declaracao/<uuid:aluno_id>/json', DeclaracaoView.as_view(), name='impressao_declaracao_json_no_slash'),
    path('declaracao/<uuid:aluno_id>/json/', DeclaracaoView.as_view(), name='impressao_declaracao_json'),

    # Certificado
    path('certificado/<uuid:aluno_id>', CertificadoImpressaoView.as_view(), name='impressao_cert_no_slash'),
    path('certificado/<uuid:aluno_id>/', CertificadoImpressaoView.as_view(), name='impressao_cert'),
    path('certificado/<uuid:aluno_id>/pdf', CertificadoPDFView.as_view(), name='impressao_cert_pdf_no_slash'),
    path('certificado/<uuid:aluno_id>/pdf/', CertificadoPDFView.as_view(), name='impressao_cert_pdf'),
    path('certificado/<uuid:aluno_id>/docx', CertificadoDOCXView.as_view(), name='impressao_cert_docx_no_slash'),
    path('certificado/<uuid:aluno_id>/docx/', CertificadoDOCXView.as_view(), name='impressao_cert_docx'),
    path('certificado/<uuid:aluno_id>/xlsx', CertificadoXLSXView.as_view(), name='impressao_cert_xlsx_no_slash'),
    path('certificado/<uuid:aluno_id>/xlsx/', CertificadoXLSXView.as_view(), name='impressao_cert_xlsx'),

    # Recibo
    path('recibo/<uuid:pagamento_id>', ReciboImpressaoView.as_view(), name='impressao_recibo_no_slash'),
    path('recibo/<uuid:pagamento_id>/', ReciboImpressaoView.as_view(), name='impressao_recibo'),
    path('recibo/<uuid:pagamento_id>/pdf', ReciboPDFView.as_view(), name='impressao_recibo_pdf_no_slash'),
    path('recibo/<uuid:pagamento_id>/pdf/', ReciboPDFView.as_view(), name='impressao_recibo_pdf'),
    path('recibo/<uuid:pagamento_id>/docx', ReciboDOCXView.as_view(), name='impressao_recibo_docx_no_slash'),
    path('recibo/<uuid:pagamento_id>/docx/', ReciboDOCXView.as_view(), name='impressao_recibo_docx'),

    # Ficha do Aluno
    path('ficha/<uuid:aluno_id>', FichaAlunoView.as_view(), name='impressao_ficha_no_slash'),
    path('ficha/<uuid:aluno_id>/', FichaAlunoView.as_view(), name='impressao_ficha'),
    path('ficha/<uuid:aluno_id>/pdf', FichaPDFView.as_view(), name='impressao_ficha_pdf_no_slash'),
    path('ficha/<uuid:aluno_id>/pdf/', FichaPDFView.as_view(), name='impressao_ficha_pdf'),
    path('ficha/<uuid:aluno_id>/docx', FichaDOCXView.as_view(), name='impressao_ficha_docx_no_slash'),
    path('ficha/<uuid:aluno_id>/docx/', FichaDOCXView.as_view(), name='impressao_ficha_docx'),
]
