from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.tenant import get_tenant_escola
from .models import AreaSeccao, AreaSeccaoDisciplina, Disciplina, DisciplinaCatalogo
from . import plano

PAPEIS_QUE_EDITAM = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA'}


class _PlanoBase(APIView):
    permission_classes = [IsAuthenticated]

    def escola(self, request):
        return get_tenant_escola(request)

    def sem_escola(self):
        return Response({'success': False, 'message': 'Nenhuma escola seleccionada.'}, status=status.HTTP_404_NOT_FOUND)

    def pode_editar(self, request):
        return getattr(request.user, 'role', '') in PAPEIS_QUE_EDITAM

    def negado(self):
        return Response({'success': False, 'message': 'O seu perfil não pode alterar o Plano Curricular.'}, status=status.HTTP_403_FORBIDDEN)

    def erro(self, mensagem, codigo=status.HTTP_400_BAD_REQUEST):
        return Response({'success': False, 'message': mensagem}, status=codigo)


def _dados_catalogo(c, usos=None):
    return {'id': str(c.id), 'nome': c.nome, 'usos': c.disciplinas_classe.count() if usos is None else usos}


class PlanoCatalogoView(_PlanoBase):
    """'Todas Disciplinas de Ensino': catálogo de qualquer disciplina, de onde se escolhem as disciplinas de cada classe."""

    def get(self, request):
        escola = self.escola(request)
        if not escola:
            return self.sem_escola()
        from django.db.models import Count
        itens = DisciplinaCatalogo.objects.filter(escola=escola).annotate(n=Count('disciplinas_classe')).order_by('nome')
        return Response({'success': True, 'data': [_dados_catalogo(c, c.n) for c in itens]})

    def post(self, request):
        if not self.pode_editar(request):
            return self.negado()
        escola = self.escola(request)
        if not escola:
            return self.sem_escola()
        brutos = request.data.get('nomes')
        if not isinstance(brutos, list):
            brutos = [request.data.get('nome')]
        criadas, repetidas, invalidas = [], [], []
        vistos = set()
        for bruto in brutos:
            nome = ' '.join(str(bruto or '').split())
            if not nome:
                continue
            if len(nome) < 2 or len(nome) > 100:
                invalidas.append(nome[:30])
                continue
            if nome.casefold() in vistos or plano.achar_no_catalogo(escola, nome):
                repetidas.append(nome)
                continue
            vistos.add(nome.casefold())
            criadas.append(DisciplinaCatalogo.objects.create(escola=escola, nome=nome))
        if not criadas and (repetidas or invalidas or not brutos):
            if repetidas and not invalidas:
                return self.erro('Esta disciplina já existe em "Todas Disciplinas de Ensino".' if len(repetidas) == 1
                                 else 'Todas essas disciplinas já existem no catálogo.', status.HTTP_409_CONFLICT)
            return self.erro('Indique o nome da disciplina (2 a 100 letras).')
        return Response({'success': True, 'data': [_dados_catalogo(c, 0) for c in criadas],
                         'repetidas': repetidas, 'invalidas': invalidas}, status=status.HTTP_201_CREATED)


class PlanoCatalogoDetalheView(_PlanoBase):
    def _item(self, request, pk):
        escola = self.escola(request)
        return escola, (DisciplinaCatalogo.objects.filter(escola=escola, pk=pk).first() if escola else None)

    def patch(self, request, pk):
        if not self.pode_editar(request):
            return self.negado()
        escola, item = self._item(request, pk)
        if not escola:
            return self.sem_escola()
        if not item:
            return self.erro('Disciplina não encontrada no catálogo.', status.HTTP_404_NOT_FOUND)
        nome = ' '.join(str(request.data.get('nome') or '').split())
        if len(nome) < 2 or len(nome) > 100:
            return self.erro('Indique um nome válido (2 a 100 letras).')
        if plano.achar_no_catalogo(escola, nome, excluir_pk=item.pk):
            return self.erro(f'Já existe "{nome}" no catálogo.', status.HTTP_409_CONFLICT)
        with transaction.atomic():
            item.nome = nome
            item.save(update_fields=['nome', 'updated_at'])
            Disciplina.objects.filter(catalogo=item).update(nome=nome)
        return Response({'success': True, 'data': _dados_catalogo(item)})

    def delete(self, request, pk):
        if not self.pode_editar(request):
            return self.negado()
        escola, item = self._item(request, pk)
        if not escola:
            return self.sem_escola()
        if not item:
            return self.erro('Disciplina não encontrada no catálogo.', status.HTTP_404_NOT_FOUND)
        usos = item.disciplinas_classe.count()
        if usos:
            return self.erro(f'Não é possível eliminar: "{item.nome}" está em {usos} classe(s). Retire-a primeiro das classes.', status.HTTP_409_CONFLICT)
        item.delete()
        return Response({'success': True, 'message': 'Disciplina eliminada do catálogo.'})


class PlanoEstruturaView(_PlanoBase):
    """Classes/Níveis com exame, áreas e totais: alimenta os filtros em cascata (turmas, matrículas, pautas)."""

    def get(self, request):
        escola = self.escola(request)
        if not escola:
            return self.sem_escola()
        return Response({'success': True, 'data': plano.estrutura(escola)})


def _dados_area(area):
    return {
        'id': str(area.id),
        'nome': area.nome,
        'classe': area.classe,
        'disciplinas': [
            {'disciplina': str(v.disciplina_id), 'tem_exame': v.tem_exame}
            for v in sorted(area.vinculos.all(), key=lambda x: x.disciplina.nome.lower())
        ],
    }


class PlanoClasseView(_PlanoBase):
    """Plano completo de UMA classe/nível: disciplinas cadastradas, áreas/secções e disciplinas de cada área."""

    def get(self, request):
        escola = self.escola(request)
        if not escola:
            return self.sem_escola()
        classe = (request.query_params.get('classe') or '').strip()
        oficial = plano.nome_classe_oficial(escola, classe)
        if not oficial:
            return self.erro('Esta classe/nível não está cadastrada no Plano Curricular.', status.HTTP_404_NOT_FOUND)

        areas = [a for a in AreaSeccao.objects.filter(escola=escola).prefetch_related('vinculos__disciplina')
                 if plano.mesma_classe(a.classe, oficial)]
        areas.sort(key=lambda a: (a.ordem, a.nome.lower()))
        discs = plano.disciplinas_da_classe(escola, oficial)
        por_disc = {}
        for a in areas:
            for v in a.vinculos.all():
                por_disc.setdefault(str(v.disciplina_id), []).append(a.nome)
        return Response({'success': True, 'data': {
            'classe': oficial,
            'tem_exame': plano.classe_tem_exame(escola, oficial),
            'disciplinas': [
                {'id': str(d.id), 'catalogo': str(d.catalogo_id) if d.catalogo_id else None,
                 'codigo': d.codigo, 'nome': d.nome, 'carga_horaria': d.carga_horaria,
                 'areas': por_disc.get(str(d.id), [])}
                for d in discs
            ],
            'areas': [_dados_area(a) for a in areas],
        }})


class PlanoAreasView(_PlanoBase):
    def post(self, request):
        if not self.pode_editar(request):
            return self.negado()
        escola = self.escola(request)
        if not escola:
            return self.sem_escola()
        oficial = plano.nome_classe_oficial(escola, request.data.get('classe'))
        if not oficial:
            return self.erro('Cadastre primeiro a Classe/Nível antes de criar Áreas/Secções.')
        nome = ' '.join(str(request.data.get('nome') or '').split())
        if len(nome) < 2:
            return self.erro('Indique o nome da Área/Secção (mínimo 2 letras).')
        if len(nome) > 80:
            return self.erro('O nome da Área/Secção é demasiado longo (máximo 80 letras).')
        if any(a.nome.strip().lower() == nome.lower() for a in plano.areas_da_classe(escola, oficial)):
            return self.erro(f"A área '{nome}' já existe na {oficial}.")
        ordem = len(plano.areas_da_classe(escola, oficial))
        area = AreaSeccao.objects.create(escola=escola, classe=oficial, nome=nome, ordem=ordem)
        return Response({'success': True, 'data': _dados_area(area)}, status=status.HTTP_201_CREATED)


class PlanoAreaDetalheView(_PlanoBase):
    def _area(self, request, pk):
        escola = self.escola(request)
        if not escola:
            return None, None
        return escola, AreaSeccao.objects.filter(escola=escola, pk=pk).first()

    def patch(self, request, pk):
        if not self.pode_editar(request):
            return self.negado()
        escola, area = self._area(request, pk)
        if not escola:
            return self.sem_escola()
        if not area:
            return self.erro('Área/Secção não encontrada.', status.HTTP_404_NOT_FOUND)
        nome = ' '.join(str(request.data.get('nome') or '').split())
        if len(nome) < 2 or len(nome) > 80:
            return self.erro('Indique um nome válido para a Área/Secção (2 a 80 letras).')
        if any(a.pk != area.pk and a.nome.strip().lower() == nome.lower() for a in plano.areas_da_classe(escola, area.classe)):
            return self.erro(f"A área '{nome}' já existe na {area.classe}.")
        area.nome = nome
        area.save(update_fields=['nome', 'updated_at'])
        for v in area.vinculos.select_related('disciplina'):
            plano.sincronizar_disciplina(v.disciplina)
        return Response({'success': True, 'data': _dados_area(area)})

    def delete(self, request, pk):
        if not self.pode_editar(request):
            return self.negado()
        escola, area = self._area(request, pk)
        if not escola:
            return self.sem_escola()
        if not area:
            return self.erro('Área/Secção não encontrada.', status.HTTP_404_NOT_FOUND)
        from apps.turmas.models import Turma
        em_uso = sum(1 for t in Turma.objects.filter(escola=escola)
                     if plano.mesma_classe(t.grau_ano, area.classe) and (t.area or '').strip().lower() == area.nome.strip().lower())
        if em_uso:
            return self.erro(f"Não é possível eliminar: {em_uso} turma(s) usam a área '{area.nome}'.", status.HTTP_409_CONFLICT)
        discs = [v.disciplina for v in area.vinculos.select_related('disciplina')]
        with transaction.atomic():
            area.delete()
            for d in discs:
                plano.sincronizar_disciplina(d)
        return Response({'success': True, 'message': 'Área/Secção eliminada.'})


class PlanoAreaDisciplinasView(_PlanoBase):
    """Define, de uma só vez, as disciplinas da Área/Secção e quais têm exame (só se a classe tiver exame)."""

    def put(self, request, pk):
        if not self.pode_editar(request):
            return self.negado()
        escola = self.escola(request)
        if not escola:
            return self.sem_escola()
        area = AreaSeccao.objects.filter(escola=escola, pk=pk).first()
        if not area:
            return self.erro('Área/Secção não encontrada.', status.HTTP_404_NOT_FOUND)
        itens = request.data.get('disciplinas')
        if not isinstance(itens, list):
            return self.erro("Envie a lista 'disciplinas' com {disciplina, tem_exame}.")

        classe_com_exame = plano.classe_tem_exame(escola, area.classe)
        validas = {str(d.id): d for d in plano.disciplinas_da_classe(escola, area.classe)}
        escolhidas = {}
        for item in itens:
            if not isinstance(item, dict):
                return self.erro('Formato inválido na lista de disciplinas.')
            did = str(item.get('disciplina') or '')
            if did not in validas:
                return self.erro('Só podem ser escolhidas disciplinas cadastradas nesta Classe/Nível.')
            tem_exame = bool(item.get('tem_exame'))
            if tem_exame and not classe_com_exame:
                return self.erro(f"A {area.classe} está definida SEM exame: não pode marcar disciplinas com exame.")
            escolhidas[did] = tem_exame

        antigas = {str(v.disciplina_id): v for v in area.vinculos.all()}
        with transaction.atomic():
            for did, v in antigas.items():
                if did not in escolhidas:
                    v.delete()
            for did, tem_exame in escolhidas.items():
                if did in antigas:
                    if antigas[did].tem_exame != tem_exame:
                        antigas[did].tem_exame = tem_exame
                        antigas[did].save(update_fields=['tem_exame'])
                else:
                    AreaSeccaoDisciplina.objects.create(escola=escola, area=area, disciplina=validas[did], tem_exame=tem_exame)
            for did in set(antigas) | set(escolhidas):
                plano.sincronizar_disciplina(validas.get(did) or antigas[did].disciplina)
        area = AreaSeccao.objects.prefetch_related('vinculos__disciplina').get(pk=area.pk)
        return Response({'success': True, 'data': _dados_area(area)})
