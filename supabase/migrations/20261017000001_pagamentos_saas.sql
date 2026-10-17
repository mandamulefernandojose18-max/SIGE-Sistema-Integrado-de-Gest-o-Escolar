-- =====================================================================
-- SIGE: Migração de Pagamentos e Controlo Automático de Assinaturas SaaS
-- Moeda: MZN (Metical) | Fuso Horário: Africa/Maputo
-- Regra Inviolável: ON DELETE RESTRICT, Proibido CASCADE, Nenhum DELETE
-- =====================================================================

-- 1. Tabela de Planos SaaS (ou extensão)
CREATE TABLE IF NOT EXISTS public.sige_saas_planos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    preco_mensal NUMERIC(12,2) NOT NULL CHECK (preco_mensal >= 0),
    limite_alunos INT NOT NULL DEFAULT 500 CHECK (limite_alunos >= 1),
    limite_professores INT NOT NULL DEFAULT 50 CHECK (limite_professores >= 1),
    limites JSONB NOT NULL DEFAULT '{"armazenamento_mb": 10240, "modulos": ["todos"]}'::jsonb,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now())
);

-- 2. Tabela de Assinaturas SaaS por Instituição
CREATE TABLE IF NOT EXISTS public.sige_saas_assinaturas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id UUID NOT NULL REFERENCES public.sige_escolas(id) ON DELETE RESTRICT,
    plano_id UUID NOT NULL REFERENCES public.sige_saas_planos(id) ON DELETE RESTRICT,
    periodicidade VARCHAR(20) NOT NULL DEFAULT 'mensal' CHECK (periodicidade IN ('mensal', 'trimestral', 'semestral', 'anual')),
    modo_data_limite VARCHAR(20) NOT NULL DEFAULT 'automatico' CHECK (modo_data_limite IN ('automatico', 'dia_fixo', 'manual')),
    dia_limite INT CHECK (dia_limite BETWEEN 1 AND 31),
    dias_tolerancia INT NOT NULL DEFAULT 5 CHECK (dias_tolerancia >= 0),
    dias_ate_suspensao INT NOT NULL DEFAULT 15 CHECK (dias_ate_suspensao >= 0),
    data_bloqueio_manual DATE,
    multa_tipo VARCHAR(20) NOT NULL DEFAULT 'nenhuma' CHECK (multa_tipo IN ('nenhuma', 'fixo', 'percentagem')),
    multa_valor NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (multa_valor >= 0),
    estado VARCHAR(30) NOT NULL DEFAULT 'activa' CHECK (estado IN ('teste', 'activa', 'fatura_pendente', 'em_atraso', 'restrita', 'suspensa', 'cancelada')),
    data_inicio TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now()),
    proxima_fatura_em DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now())
);

-- 3. Tabela de Faturas SaaS
CREATE TABLE IF NOT EXISTS public.sige_saas_faturas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assinatura_id UUID NOT NULL REFERENCES public.sige_saas_assinaturas(id) ON DELETE RESTRICT,
    instituicao_id UUID NOT NULL REFERENCES public.sige_escolas(id) ON DELETE RESTRICT,
    numero_fatura VARCHAR(50) NOT NULL,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    valor NUMERIC(12,2) NOT NULL CHECK (valor >= 0),
    multa_aplicada NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (multa_aplicada >= 0),
    valor_pago NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (valor_pago >= 0),
    data_abertura DATE NOT NULL,
    data_limite DATE NOT NULL,
    data_limite_manual DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'aberta' CHECK (estado IN ('aberta', 'paga_parcial', 'paga', 'em_atraso', 'anulada')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now()),
    CONSTRAINT uq_fatura_assinatura_periodo UNIQUE (assinatura_id, periodo_inicio)
);

-- 4. Tabela de Pagamentos SaaS com Comprovativo
CREATE TABLE IF NOT EXISTS public.sige_saas_pagamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fatura_id UUID NOT NULL REFERENCES public.sige_saas_faturas(id) ON DELETE RESTRICT,
    instituicao_id UUID NOT NULL REFERENCES public.sige_escolas(id) ON DELETE RESTRICT,
    metodo VARCHAR(50) NOT NULL CHECK (metodo IN ('M-Pesa', 'e-Mola', 'transferencia_bancaria', 'numerario')),
    referencia VARCHAR(100) NOT NULL,
    valor NUMERIC(12,2) NOT NULL CHECK (valor > 0),
    comprovativo_path TEXT,
    comprovativo_url TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'enviado' CHECK (estado IN ('enviado', 'confirmado', 'rejeitado')),
    confirmado_por VARCHAR(150),
    confirmado_em TIMESTAMPTZ,
    motivo_rejeicao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now())
);

-- 5. Tabela de Auditoria Imutável (Log de Assinaturas)
CREATE TABLE IF NOT EXISTS public.sige_saas_log_assinaturas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id UUID NOT NULL REFERENCES public.sige_escolas(id) ON DELETE RESTRICT,
    assinatura_id UUID REFERENCES public.sige_saas_assinaturas(id) ON DELETE RESTRICT,
    fatura_id UUID REFERENCES public.sige_saas_faturas(id) ON DELETE RESTRICT,
    accao VARCHAR(100) NOT NULL,
    estado_anterior VARCHAR(50),
    estado_novo VARCHAR(50),
    valor_anterior NUMERIC(12,2),
    valor_novo NUMERIC(12,2),
    feito_por VARCHAR(150) NOT NULL DEFAULT 'sistema',
    motivo TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now())
);

-- Índices de Alta Eficiência
CREATE INDEX IF NOT EXISTS idx_saas_assinaturas_instituicao ON public.sige_saas_assinaturas(instituicao_id);
CREATE INDEX IF NOT EXISTS idx_saas_assinaturas_estado ON public.sige_saas_assinaturas(estado);
CREATE INDEX IF NOT EXISTS idx_saas_faturas_instituicao ON public.sige_saas_faturas(instituicao_id);
CREATE INDEX IF NOT EXISTS idx_saas_faturas_estado ON public.sige_saas_faturas(estado);
CREATE INDEX IF NOT EXISTS idx_saas_faturas_data_limite ON public.sige_saas_faturas(data_limite);
CREATE INDEX IF NOT EXISTS idx_saas_pagamentos_fatura ON public.sige_saas_pagamentos(fatura_id);
CREATE INDEX IF NOT EXISTS idx_saas_pagamentos_instituicao ON public.sige_saas_pagamentos(instituicao_id);
CREATE INDEX IF NOT EXISTS idx_saas_pagamentos_estado ON public.sige_saas_pagamentos(estado);
CREATE INDEX IF NOT EXISTS idx_saas_logs_instituicao ON public.sige_saas_log_assinaturas(instituicao_id);
CREATE INDEX IF NOT EXISTS idx_saas_logs_criado_em ON public.sige_saas_log_assinaturas(criado_em);

-- =====================================================================
-- 🛡️ REGRA CRÍTICA INVIOLÁVEL: BLOQUEIO TOTAL DE DELETE E TRUNCATE
-- =====================================================================

CREATE OR REPLACE FUNCTION public.fn_proibir_delecao_saas()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Eliminação não permitida: os dados da instituição e os registos de assinaturas e faturas são invioláveis e permanentes.'
        USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_proibir_delete_assinaturas ON public.sige_saas_assinaturas;
CREATE TRIGGER trg_proibir_delete_assinaturas
    BEFORE DELETE ON public.sige_saas_assinaturas
    FOR EACH ROW EXECUTE FUNCTION public.fn_proibir_delecao_saas();

DROP TRIGGER IF EXISTS trg_proibir_delete_faturas ON public.sige_saas_faturas;
CREATE TRIGGER trg_proibir_delete_faturas
    BEFORE DELETE ON public.sige_saas_faturas
    FOR EACH ROW EXECUTE FUNCTION public.fn_proibir_delecao_saas();

DROP TRIGGER IF EXISTS trg_proibir_delete_pagamentos ON public.sige_saas_pagamentos;
CREATE TRIGGER trg_proibir_delete_pagamentos
    BEFORE DELETE ON public.sige_saas_pagamentos
    FOR EACH ROW EXECUTE FUNCTION public.fn_proibir_delecao_saas();

DROP TRIGGER IF EXISTS trg_proibir_delete_log_assinaturas ON public.sige_saas_log_assinaturas;
CREATE TRIGGER trg_proibir_delete_log_assinaturas
    BEFORE DELETE ON public.sige_saas_log_assinaturas
    FOR EACH ROW EXECUTE FUNCTION public.fn_proibir_delecao_saas();

-- Revogar DELETE e TRUNCATE em tabelas críticas para anon e authenticated
REVOKE DELETE, TRUNCATE ON public.sige_saas_assinaturas FROM anon, authenticated;
REVOKE DELETE, TRUNCATE ON public.sige_saas_faturas FROM anon, authenticated;
REVOKE DELETE, TRUNCATE ON public.sige_saas_pagamentos FROM anon, authenticated;
REVOKE DELETE, TRUNCATE ON public.sige_saas_log_assinaturas FROM anon, authenticated;
REVOKE DELETE, TRUNCATE ON public.sige_escolas FROM anon, authenticated;

-- =====================================================================
-- ⚙️ FUNÇÕES PL/PGSQL TRANSACIONAIS (RPC)
-- =====================================================================

-- 1. data_limite_efectiva(fatura_id): Calcula a data efectiva com prioridade estrita
CREATE OR REPLACE FUNCTION public.data_limite_efectiva(p_fatura_id UUID)
RETURNS DATE AS $$
DECLARE
    v_fatura RECORD;
    v_assinatura RECORD;
    v_ano INT;
    v_mes INT;
    v_dia_fixo INT;
    v_ultimo_dia_mes INT;
BEGIN
    SELECT * INTO v_fatura FROM public.sige_saas_faturas WHERE id = p_fatura_id;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Prioridade 1: Data manual na fatura
    IF v_fatura.data_limite_manual IS NOT NULL THEN
        RETURN v_fatura.data_limite_manual;
    END IF;

    SELECT * INTO v_assinatura FROM public.sige_saas_assinaturas WHERE id = v_fatura.assinatura_id;
    IF NOT FOUND THEN
        RETURN v_fatura.data_limite;
    END IF;

    -- Prioridade 2: Modo dia_fixo
    IF v_assinatura.modo_data_limite = 'dia_fixo' AND v_assinatura.dia_limite IS NOT NULL THEN
        v_ano := EXTRACT(YEAR FROM v_fatura.periodo_inicio);
        v_mes := EXTRACT(MONTH FROM v_fatura.periodo_inicio);
        -- Último dia do mês
        v_ultimo_dia_mes := EXTRACT(DAY FROM (DATE_TRUNC('month', v_fatura.periodo_inicio) + INTERVAL '1 month - 1 day')::date);
        v_dia_fixo := LEAST(v_assinatura.dia_limite, v_ultimo_dia_mes);
        RETURN MAKE_DATE(v_ano, v_mes, v_dia_fixo);
    END IF;

    -- Prioridade 3: Predefinição da periodicidade
    IF v_assinatura.modo_data_limite = 'automatico' THEN
        v_ano := EXTRACT(YEAR FROM v_fatura.periodo_inicio);
        v_mes := EXTRACT(MONTH FROM v_fatura.periodo_inicio);
        IF v_assinatura.periodicidade = 'mensal' THEN
            -- Mensal: dia 10
            RETURN MAKE_DATE(v_ano, v_mes, 10);
        ELSIF v_assinatura.periodicidade = 'trimestral' THEN
            -- Trimestral: dia 15 do 1º mês
            RETURN MAKE_DATE(v_ano, v_mes, 15);
        ELSIF v_assinatura.periodicidade = 'semestral' THEN
            -- Semestral: dia 30 do 1º mês
            v_ultimo_dia_mes := EXTRACT(DAY FROM (DATE_TRUNC('month', v_fatura.periodo_inicio) + INTERVAL '1 month - 1 day')::date);
            RETURN MAKE_DATE(v_ano, v_mes, LEAST(30, v_ultimo_dia_mes));
        ELSIF v_assinatura.periodicidade = 'anual' THEN
            -- Anual: 31 de Janeiro
            RETURN MAKE_DATE(v_ano, 1, 31);
        END IF;
    END IF;

    RETURN v_fatura.data_limite;
END;
$$ LANGUAGE plpgsql STABLE;

-- 2. gerar_faturas_do_dia(): Cria faturas dos períodos com idempotência ON CONFLICT
CREATE OR REPLACE FUNCTION public.gerar_faturas_do_dia()
RETURNS INT AS $$
DECLARE
    v_hoje DATE := (timezone('Africa/Maputo', now()))::date;
    v_ass RECORD;
    v_plano RECORD;
    v_periodo_inicio DATE;
    v_periodo_fim DATE;
    v_proxima_fatura DATE;
    v_data_limite DATE;
    v_valor NUMERIC(12,2);
    v_num_fatura TEXT;
    v_faturas_geradas INT := 0;
BEGIN
    -- Advisory Lock para impedir execuções simultâneas
    PERFORM pg_advisory_xact_lock(849204921);

    FOR v_ass IN
        SELECT a.*, e.nome as escola_nome
        FROM public.sige_saas_assinaturas a
        JOIN public.sige_escolas e ON e.id = a.instituicao_id
        WHERE a.estado NOT IN ('cancelada')
          AND a.proxima_fatura_em <= v_hoje
    LOOP
        SELECT * INTO v_plano FROM public.sige_saas_planos WHERE id = v_ass.plano_id;
        
        v_periodo_inicio := v_ass.proxima_fatura_em;

        -- Definir duração e valor conforme periodicidade
        IF v_ass.periodicidade = 'mensal' THEN
            v_periodo_fim := (v_periodo_inicio + INTERVAL '1 month - 1 day')::date;
            v_proxima_fatura := (v_periodo_inicio + INTERVAL '1 month')::date;
            v_valor := v_plano.preco_mensal;
            v_data_limite := MAKE_DATE(EXTRACT(YEAR FROM v_periodo_inicio)::int, EXTRACT(MONTH FROM v_periodo_inicio)::int, 10);
        ELSIF v_ass.periodicidade = 'trimestral' THEN
            v_periodo_fim := (v_periodo_inicio + INTERVAL '3 months - 1 day')::date;
            v_proxima_fatura := (v_periodo_inicio + INTERVAL '3 months')::date;
            v_valor := v_plano.preco_mensal * 3 * 0.95; -- 5% desconto trimestral
            v_data_limite := MAKE_DATE(EXTRACT(YEAR FROM v_periodo_inicio)::int, EXTRACT(MONTH FROM v_periodo_inicio)::int, 15);
        ELSIF v_ass.periodicidade = 'semestral' THEN
            v_periodo_fim := (v_periodo_inicio + INTERVAL '6 months - 1 day')::date;
            v_proxima_fatura := (v_periodo_inicio + INTERVAL '6 months')::date;
            v_valor := v_plano.preco_mensal * 6 * 0.90; -- 10% desconto semestral
            v_data_limite := (DATE_TRUNC('month', v_periodo_inicio) + INTERVAL '29 days')::date;
        ELSIF v_ass.periodicidade = 'anual' THEN
            v_periodo_fim := (v_periodo_inicio + INTERVAL '1 year - 1 day')::date;
            v_proxima_fatura := (v_periodo_inicio + INTERVAL '1 year')::date;
            v_valor := v_plano.preco_mensal * 12 * 0.85; -- 15% desconto anual
            v_data_limite := MAKE_DATE(EXTRACT(YEAR FROM v_periodo_inicio)::int, 1, 31);
        END IF;

        -- Ajuste se modo dia_fixo
        IF v_ass.modo_data_limite = 'dia_fixo' AND v_ass.dia_limite IS NOT NULL THEN
            v_data_limite := MAKE_DATE(
                EXTRACT(YEAR FROM v_periodo_inicio)::int,
                EXTRACT(MONTH FROM v_periodo_inicio)::int,
                LEAST(v_ass.dia_limite, EXTRACT(DAY FROM (DATE_TRUNC('month', v_periodo_inicio) + INTERVAL '1 month - 1 day')::date)::int)
            );
        END IF;

        v_num_fatura := 'FAT-' || TO_CHAR(v_periodo_inicio, 'YYYYMM') || '-' || SUBSTRING(v_ass.instituicao_id::text FROM 1 FOR 6);

        -- Inserção idempotente com ON CONFLICT DO NOTHING
        INSERT INTO public.sige_saas_faturas (
            assinatura_id, instituicao_id, numero_fatura, periodo_inicio, periodo_fim,
            valor, data_abertura, data_limite, estado
        )
        VALUES (
            v_ass.id, v_ass.instituicao_id, v_num_fatura, v_periodo_inicio, v_periodo_fim,
            v_valor, v_hoje, v_data_limite, 'aberta'
        )
        ON CONFLICT (assinatura_id, periodo_inicio) DO NOTHING;

        IF FOUND THEN
            v_faturas_geradas := v_faturas_geradas + 1;
            
            -- Actualiza próxima fatura da assinatura
            UPDATE public.sige_saas_assinaturas
            SET proxima_fatura_em = v_proxima_fatura,
                estado = CASE WHEN estado = 'activa' THEN 'fatura_pendente' ELSE estado END,
                updated_at = timezone('Africa/Maputo', now())
            WHERE id = v_ass.id;

            -- Auditoria
            INSERT INTO public.sige_saas_log_assinaturas (
                instituicao_id, assinatura_id, accao, estado_anterior, estado_novo,
                valor_novo, feito_por, motivo
            )
            VALUES (
                v_ass.instituicao_id, v_ass.id, 'GERAR_FATURA_AUTOMATICA', v_ass.estado,
                'fatura_pendente', v_valor, 'sistema', 'Abertura automática de janela de cobrança para o período ' || v_periodo_inicio
            );
        END IF;
    END LOOP;

    RETURN v_faturas_geradas;
END;
$$ LANGUAGE plpgsql;

-- 3. actualizar_estados_assinaturas(): Aplica em_atraso → restrita → suspensa
CREATE OR REPLACE FUNCTION public.actualizar_estados_assinaturas()
RETURNS JSONB AS $$
DECLARE
    v_hoje DATE := (timezone('Africa/Maputo', now()))::date;
    v_fat RECORD;
    v_ass RECORD;
    v_data_efectiva DATE;
    v_limite_tolerancia DATE;
    v_limite_suspensao DATE;
    v_novo_estado VARCHAR(30);
    v_multa_calculada NUMERIC(12,2);
    v_alteracoes INT := 0;
BEGIN
    PERFORM pg_advisory_xact_lock(849204922);

    FOR v_fat IN
        SELECT f.*, a.dias_tolerancia, a.dias_ate_suspensao, a.data_bloqueio_manual,
               a.multa_tipo, a.multa_valor, a.estado as ass_estado
        FROM public.sige_saas_faturas f
        JOIN public.sige_saas_assinaturas a ON a.id = f.assinatura_id
        WHERE f.estado IN ('aberta', 'paga_parcial', 'em_atraso')
    LOOP
        v_data_efectiva := public.data_limite_efectiva(v_fat.id);
        v_limite_tolerancia := v_data_efectiva + v_fat.dias_tolerancia;
        v_limite_suspensao := v_limite_tolerancia + v_fat.dias_ate_suspensao;

        -- Cálculo de Multa caso ultrapasse a data efectiva
        IF v_hoje > v_data_efectiva AND v_fat.multa_aplicada = 0 THEN
            IF v_fat.multa_tipo = 'fixo' THEN
                v_multa_calculada := v_fat.multa_valor;
            ELSIF v_fat.multa_tipo = 'percentagem' THEN
                v_multa_calculada := ROUND(v_fat.valor * (v_fat.multa_valor / 100.0), 2);
            ELSE
                v_multa_calculada := 0.00;
            END IF;

            IF v_multa_calculada > 0 THEN
                UPDATE public.sige_saas_faturas
                SET multa_aplicada = v_multa_calculada,
                    updated_at = timezone('Africa/Maputo', now())
                WHERE id = v_fat.id;
            END IF;
        END IF;

        -- Se a data de vencimento passou, marca a fatura como em_atraso
        IF v_hoje > v_data_efectiva AND v_fat.estado != 'em_atraso' THEN
            UPDATE public.sige_saas_faturas
            SET estado = 'em_atraso', updated_at = timezone('Africa/Maputo', now())
            WHERE id = v_fat.id;
        END IF;

        -- Avaliação do Estado da Assinatura da Escola
        IF v_fat.ass_estado NOT IN ('cancelada') THEN
            v_novo_estado := v_fat.ass_estado;

            -- 1. Bloqueio por data_bloqueio_manual
            IF v_fat.data_bloqueio_manual IS NOT NULL AND v_hoje >= v_fat.data_bloqueio_manual THEN
                v_novo_estado := 'suspensa';
            -- 2. Ultrapassou dias até suspensão
            ELSIF v_hoje >= v_limite_suspensao THEN
                v_novo_estado := 'suspensa';
            -- 3. Ultrapassou dias de tolerância -> Restrita (Só leitura)
            ELSIF v_hoje > v_limite_tolerancia THEN
                v_novo_estado := 'restrita';
            -- 4. Ultrapassou a data limite mas dentro da tolerância -> Em atraso (com aviso)
            ELSIF v_hoje > v_data_efectiva THEN
                v_novo_estado := 'em_atraso';
            END IF;

            IF v_novo_estado != v_fat.ass_estado THEN
                UPDATE public.sige_saas_assinaturas
                SET estado = v_novo_estado, updated_at = timezone('Africa/Maputo', now())
                WHERE id = v_fat.assinatura_id;

                -- Atualiza status da sige_escolas para manter retrocompatibilidade
                UPDATE public.sige_escolas
                SET status = CASE 
                    WHEN v_novo_estado = 'suspensa' THEN 'SUSPENSA'
                    WHEN v_novo_estado = 'cancelada' THEN 'EXPIRADA'
                    ELSE 'ATIVA'
                END
                WHERE id = v_fat.instituicao_id;

                INSERT INTO public.sige_saas_log_assinaturas (
                    instituicao_id, assinatura_id, fatura_id, accao,
                    estado_anterior, estado_novo, feito_por, motivo
                )
                VALUES (
                    v_fat.instituicao_id, v_fat.assinatura_id, v_fat.id, 'TRANSICAO_AUTOMATICA_ESTADO',
                    v_fat.ass_estado, v_novo_estado, 'sistema',
                    'Transição automática de estado por vencimento/tolerância (Hoje: ' || v_hoje || ')'
                );

                v_alteracoes := v_alteracoes + 1;
            END IF;
        END IF;
    END LOOP;

    RETURN jsonb_build_object(
        'sucesso', true,
        'data_execucao', v_hoje,
        'alteracoes_processadas', v_alteracoes
    );
END;
$$ LANGUAGE plpgsql;

-- 4. confirmar_pagamento(pagamento_id, utilizador)
CREATE OR REPLACE FUNCTION public.confirmar_pagamento(p_pagamento_id UUID, p_utilizador TEXT)
RETURNS JSONB AS $$
DECLARE
    v_pag RECORD;
    v_fat RECORD;
    v_ass RECORD;
    v_faturas_atraso_restantes INT;
    v_novo_valor_pago NUMERIC(12,2);
    v_total_devido NUMERIC(12,2);
    v_sobra NUMERIC(12,2) := 0;
BEGIN
    SELECT * INTO v_pag FROM public.sige_saas_pagamentos WHERE id = p_pagamento_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Registo de pagamento % não encontrado.', p_pagamento_id;
    END IF;

    IF v_pag.estado = 'confirmado' THEN
        RETURN jsonb_build_object('sucesso', true, 'mensagem', 'Pagamento já se encontrava confirmado.');
    END IF;

    SELECT * INTO v_fat FROM public.sige_saas_faturas WHERE id = v_pag.fatura_id FOR UPDATE;
    SELECT * INTO v_ass FROM public.sige_saas_assinaturas WHERE id = v_fat.assinatura_id FOR UPDATE;

    v_total_devido := v_fat.valor + v_fat.multa_aplicada;
    v_novo_valor_pago := v_fat.valor_pago + v_pag.valor;

    -- Actualiza o pagamento
    UPDATE public.sige_saas_pagamentos
    SET estado = 'confirmado',
        confirmado_por = COALESCE(p_utilizador, 'Super Admin'),
        confirmado_em = timezone('Africa/Maputo', now()),
        updated_at = timezone('Africa/Maputo', now())
    WHERE id = p_pagamento_id;

    -- Actualiza a fatura
    IF v_novo_valor_pago >= v_total_devido THEN
        v_sobra := v_novo_valor_pago - v_total_devido;
        UPDATE public.sige_saas_faturas
        SET valor_pago = v_novo_valor_pago,
            estado = 'paga',
            updated_at = timezone('Africa/Maputo', now())
        WHERE id = v_fat.id;
    ELSE
        UPDATE public.sige_saas_faturas
        SET valor_pago = v_novo_valor_pago,
            estado = 'paga_parcial',
            updated_at = timezone('Africa/Maputo', now())
        WHERE id = v_fat.id;
    END IF;

    -- Abater sobra em faturas futuras se houver excedente
    IF v_sobra > 0 THEN
        UPDATE public.sige_saas_faturas
        SET valor_pago = valor_pago + v_sobra,
            estado = CASE WHEN valor_pago + v_sobra >= (valor + multa_aplicada) THEN 'paga' ELSE 'paga_parcial' END,
            updated_at = timezone('Africa/Maputo', now())
        WHERE id = (
            SELECT id FROM public.sige_saas_faturas
            WHERE assinatura_id = v_ass.id AND estado IN ('aberta', 'paga_parcial') AND id != v_fat.id
            ORDER BY periodo_inicio ASC
            LIMIT 1
        );
    END IF;

    -- Verificar se restam faturas em atraso ou abertas
    SELECT COUNT(*) INTO v_faturas_atraso_restantes
    FROM public.sige_saas_faturas
    WHERE instituicao_id = v_pag.instituicao_id AND estado IN ('em_atraso', 'aberta');

    -- Se não existirem faturas em atraso, reactiva a assinatura automaticamente
    IF v_faturas_atraso_restantes = 0 THEN
        UPDATE public.sige_saas_assinaturas
        SET estado = 'activa', updated_at = timezone('Africa/Maputo', now())
        WHERE id = v_ass.id;

        UPDATE public.sige_escolas
        SET status = 'ATIVA', bloqueada_manualmente = FALSE
        WHERE id = v_pag.instituicao_id;
    END IF;

    INSERT INTO public.sige_saas_log_assinaturas (
        instituicao_id, assinatura_id, fatura_id, accao,
        estado_anterior, estado_novo, valor_novo, feito_por, motivo
    )
    VALUES (
        v_pag.instituicao_id, v_ass.id, v_fat.id, 'PAGAMENTO_CONFIRMADO',
        v_ass.estado, (CASE WHEN v_faturas_atraso_restantes = 0 THEN 'activa' ELSE v_ass.estado END),
        v_pag.valor, COALESCE(p_utilizador, 'Super Admin'),
        'Confirmação de pagamento Ref: ' || v_pag.referencia || ' no valor de ' || v_pag.valor || ' MZN'
    );

    RETURN jsonb_build_object(
        'sucesso', true,
        'mensagem', 'Pagamento confirmado com sucesso.',
        'fatura_estado', (CASE WHEN v_novo_valor_pago >= v_total_devido THEN 'paga' ELSE 'paga_parcial' END),
        'assinatura_reativada', (v_faturas_atraso_restantes = 0)
    );
END;
$$ LANGUAGE plpgsql;

-- 5. rejeitar_pagamento(pagamento_id, motivo, utilizador)
CREATE OR REPLACE FUNCTION public.rejeitar_pagamento(p_pagamento_id UUID, p_motivo TEXT, p_utilizador TEXT)
RETURNS JSONB AS $$
DECLARE
    v_pag RECORD;
BEGIN
    IF p_motivo IS NULL OR TRIM(p_motivo) = '' THEN
        RAISE EXCEPTION 'O motivo de rejeição é estritamente obrigatório.';
    END IF;

    SELECT * INTO v_pag FROM public.sige_saas_pagamentos WHERE id = p_pagamento_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pagamento % não encontrado.', p_pagamento_id;
    END IF;

    UPDATE public.sige_saas_pagamentos
    SET estado = 'rejeitado',
        motivo_rejeicao = p_motivo,
        confirmado_por = COALESCE(p_utilizador, 'Super Admin'),
        confirmado_em = timezone('Africa/Maputo', now()),
        updated_at = timezone('Africa/Maputo', now())
    WHERE id = p_pagamento_id;

    INSERT INTO public.sige_saas_log_assinaturas (
        instituicao_id, fatura_id, accao, estado_anterior, estado_novo,
        feito_por, motivo
    )
    VALUES (
        v_pag.instituicao_id, v_pag.fatura_id, 'PAGAMENTO_REJEITADO',
        'enviado', 'rejeitado', COALESCE(p_utilizador, 'Super Admin'),
        p_motivo
    );

    RETURN jsonb_build_object('sucesso', true, 'mensagem', 'Pagamento rejeitado com sucesso.');
END;
$$ LANGUAGE plpgsql;

-- 6. prorrogar_data_limite(fatura_id, nova_data, motivo, utilizador)
CREATE OR REPLACE FUNCTION public.prorrogar_data_limite(p_fatura_id UUID, p_nova_data DATE, p_motivo TEXT, p_utilizador TEXT)
RETURNS JSONB AS $$
DECLARE
    v_fat RECORD;
    v_ass RECORD;
BEGIN
    IF p_motivo IS NULL OR TRIM(p_motivo) = '' THEN
        RAISE EXCEPTION 'O motivo da prorrogação de prazo é estritamente obrigatório.';
    END IF;

    SELECT * INTO v_fat FROM public.sige_saas_faturas WHERE id = p_fatura_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Fatura % não encontrada.', p_fatura_id;
    END IF;

    IF p_nova_data <= v_fat.periodo_inicio THEN
        RAISE EXCEPTION 'A nova data limite deve ser posterior à data de início do período.';
    END IF;

    SELECT * INTO v_ass FROM public.sige_saas_assinaturas WHERE id = v_fat.assinatura_id FOR UPDATE;

    UPDATE public.sige_saas_faturas
    SET data_limite_manual = p_nova_data,
        estado = CASE WHEN estado = 'em_atraso' AND p_nova_data >= (timezone('Africa/Maputo', now()))::date THEN 'aberta' ELSE estado END,
        updated_at = timezone('Africa/Maputo', now())
    WHERE id = p_fatura_id;

    -- Se a prorrogação reabre o prazo e a assinatura estava em restrita/suspensa, devolve para activa
    IF p_nova_data >= (timezone('Africa/Maputo', now()))::date AND v_ass.estado IN ('em_atraso', 'restrita', 'suspensa') THEN
        UPDATE public.sige_saas_assinaturas
        SET estado = 'fatura_pendente', updated_at = timezone('Africa/Maputo', now())
        WHERE id = v_ass.id;

        UPDATE public.sige_escolas SET status = 'ATIVA' WHERE id = v_fat.instituicao_id;
    END IF;

    INSERT INTO public.sige_saas_log_assinaturas (
        instituicao_id, assinatura_id, fatura_id, accao,
        estado_anterior, estado_novo, feito_por, motivo
    )
    VALUES (
        v_fat.instituicao_id, v_ass.id, v_fat.id, 'PRORROGAR_DATA_LIMITE',
        v_ass.estado, 'fatura_pendente', COALESCE(p_utilizador, 'Super Admin'),
        'Prorrogação de data-limite para ' || p_nova_data || '. Motivo: ' || p_motivo
    );

    RETURN jsonb_build_object('sucesso', true, 'mensagem', 'Prazo prorrogado com sucesso.', 'nova_data', p_nova_data);
END;
$$ LANGUAGE plpgsql;

-- 7. suspender_manual(instituicao_id, motivo, utilizador)
CREATE OR REPLACE FUNCTION public.suspender_manual(p_instituicao_id UUID, p_motivo TEXT, p_utilizador TEXT)
RETURNS JSONB AS $$
DECLARE
    v_ass RECORD;
BEGIN
    IF p_motivo IS NULL OR TRIM(p_motivo) = '' THEN
        RAISE EXCEPTION 'A justificação de suspensão manual é estritamente obrigatória.';
    END IF;

    SELECT * INTO v_ass FROM public.sige_saas_assinaturas WHERE instituicao_id = p_instituicao_id ORDER BY created_at DESC LIMIT 1 FOR UPDATE;

    UPDATE public.sige_saas_assinaturas
    SET estado = 'suspensa', updated_at = timezone('Africa/Maputo', now())
    WHERE instituicao_id = p_instituicao_id;

    UPDATE public.sige_escolas
    SET status = 'SUSPENSA', bloqueada_manualmente = TRUE
    WHERE id = p_instituicao_id;

    INSERT INTO public.sige_saas_log_assinaturas (
        instituicao_id, assinatura_id, accao, estado_anterior, estado_novo,
        feito_por, motivo
    )
    VALUES (
        p_instituicao_id, v_ass.id, 'SUSPENSAO_MANUAL',
        COALESCE(v_ass.estado, 'activa'), 'suspensa', COALESCE(p_utilizador, 'Super Admin'),
        p_motivo
    );

    RETURN jsonb_build_object('sucesso', true, 'mensagem', 'Instituição suspensa manualmente.');
END;
$$ LANGUAGE plpgsql;

-- 8. reactivar_manual(instituicao_id, motivo, utilizador)
CREATE OR REPLACE FUNCTION public.reactivar_manual(p_instituicao_id UUID, p_motivo TEXT, p_utilizador TEXT)
RETURNS JSONB AS $$
DECLARE
    v_ass RECORD;
BEGIN
    IF p_motivo IS NULL OR TRIM(p_motivo) = '' THEN
        RAISE EXCEPTION 'A justificação de reactivação manual é estritamente obrigatória.';
    END IF;

    SELECT * INTO v_ass FROM public.sige_saas_assinaturas WHERE instituicao_id = p_instituicao_id ORDER BY created_at DESC LIMIT 1 FOR UPDATE;

    UPDATE public.sige_saas_assinaturas
    SET estado = 'activa', updated_at = timezone('Africa/Maputo', now())
    WHERE instituicao_id = p_instituicao_id;

    UPDATE public.sige_escolas
    SET status = 'ATIVA', bloqueada_manualmente = FALSE
    WHERE id = p_instituicao_id;

    INSERT INTO public.sige_saas_log_assinaturas (
        instituicao_id, assinatura_id, accao, estado_anterior, estado_novo,
        feito_por, motivo
    )
    VALUES (
        p_instituicao_id, v_ass.id, 'REACTIVACAO_MANUAL',
        COALESCE(v_ass.estado, 'suspensa'), 'activa', COALESCE(p_utilizador, 'Super Admin'),
        p_motivo
    );

    RETURN jsonb_build_object('sucesso', true, 'mensagem', 'Instituição reactivada com sucesso.');
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 🔒 POLÍTICAS DE ROW LEVEL SECURITY (RLS)
-- =====================================================================

ALTER TABLE public.sige_saas_planos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_saas_assinaturas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_saas_faturas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_saas_pagamentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_saas_log_assinaturas ENABLE ROW LEVEL SECURITY;

-- Service Role e Postgres possuem permissão irrestrita
CREATE POLICY "service_all_saas_planos" ON public.sige_saas_planos FOR ALL
USING (current_user = 'postgres' OR (current_setting('request.jwt.claim.role', true) = 'service_role'));

CREATE POLICY "service_all_saas_assinaturas" ON public.sige_saas_assinaturas FOR ALL
USING (current_user = 'postgres' OR (current_setting('request.jwt.claim.role', true) = 'service_role'));

CREATE POLICY "service_all_saas_faturas" ON public.sige_saas_faturas FOR ALL
USING (current_user = 'postgres' OR (current_setting('request.jwt.claim.role', true) = 'service_role'));

CREATE POLICY "service_all_saas_pagamentos" ON public.sige_saas_pagamentos FOR ALL
USING (current_user = 'postgres' OR (current_setting('request.jwt.claim.role', true) = 'service_role'));

CREATE POLICY "service_all_saas_log" ON public.sige_saas_log_assinaturas FOR ALL
USING (current_user = 'postgres' OR (current_setting('request.jwt.claim.role', true) = 'service_role'));

-- Leitura pública de planos activos
CREATE POLICY "public_read_saas_planos" ON public.sige_saas_planos FOR SELECT USING (activo = true);

-- Isolamento Multi-Tenant para Instituições Autenticadas
CREATE POLICY "tenant_read_saas_assinaturas" ON public.sige_saas_assinaturas FOR SELECT
USING (instituicao_id::text = current_setting('request.jwt.claim.escola_id', true));

CREATE POLICY "tenant_read_saas_faturas" ON public.sige_saas_faturas FOR SELECT
USING (instituicao_id::text = current_setting('request.jwt.claim.escola_id', true));

CREATE POLICY "tenant_read_saas_pagamentos" ON public.sige_saas_pagamentos FOR SELECT
USING (instituicao_id::text = current_setting('request.jwt.claim.escola_id', true));

CREATE POLICY "tenant_insert_saas_pagamentos" ON public.sige_saas_pagamentos FOR INSERT
WITH CHECK (instituicao_id::text = current_setting('request.jwt.claim.escola_id', true) AND estado = 'enviado');

CREATE POLICY "tenant_read_saas_log" ON public.sige_saas_log_assinaturas FOR SELECT
USING (instituicao_id::text = current_setting('request.jwt.claim.escola_id', true));

-- 6. Tabela de Coordenadas e Contas Oficiais de Pagamento SaaS
CREATE TABLE IF NOT EXISTS public.sige_saas_coordenadas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mpesa_numero VARCHAR(50) NOT NULL DEFAULT '',
    mpesa_titular VARCHAR(150) NOT NULL DEFAULT '',
    emola_numero VARCHAR(50) NOT NULL DEFAULT '',
    emola_titular VARCHAR(150) NOT NULL DEFAULT '',
    bim_conta VARCHAR(50) NOT NULL DEFAULT '',
    bim_nib VARCHAR(50) NOT NULL DEFAULT '',
    bim_titular VARCHAR(150) NOT NULL DEFAULT '',
    bci_conta VARCHAR(50) NOT NULL DEFAULT '',
    bci_nib VARCHAR(50) NOT NULL DEFAULT '',
    bci_titular VARCHAR(150) NOT NULL DEFAULT '',
    nuit_entidade VARCHAR(50) NOT NULL DEFAULT '',
    instrucoes_adicionais TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('Africa/Maputo', now())
);

ALTER TABLE public.sige_saas_coordenadas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_all_saas_coordenadas" ON public.sige_saas_coordenadas FOR ALL
USING (current_user = 'postgres' OR (current_setting('request.jwt.claim.role', true) = 'service_role'));

CREATE POLICY "public_read_saas_coordenadas" ON public.sige_saas_coordenadas FOR SELECT USING (true);
