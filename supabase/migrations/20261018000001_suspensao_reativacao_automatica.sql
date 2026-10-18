-- =====================================================================
-- SIGE SaaS — Migração: Suspensão e Reactivação Automáticas (Africa/Maputo)
-- Suporta operações manuais e automáticas integradas
-- =====================================================================

-- 1. Função: avaliar_regras_automaticas(instituicao_id, acao_desejada, utilizador)
CREATE OR REPLACE FUNCTION public.avaliar_regras_automaticas(
    p_instituicao_id UUID,
    p_acao_desejada TEXT,
    p_utilizador TEXT
)
RETURNS JSONB AS $$
DECLARE
    v_hoje DATE := (timezone('Africa/Maputo', now()))::date;
    v_ass RECORD;
    v_faturas_corte_count INT := 0;
    v_faturas_restricao_count INT := 0;
    v_faturas_tolerancia_count INT := 0;
    v_faturas_abertas_count INT := 0;
    v_novo_estado VARCHAR(30);
    v_novo_status_escola VARCHAR(20);
    v_accao_log VARCHAR(50);
    v_motivo TEXT;
BEGIN
    SELECT * INTO v_ass 
    FROM public.sige_saas_assinaturas 
    WHERE instituicao_id = p_instituicao_id 
    ORDER BY created_at DESC 
    LIMIT 1 
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('sucesso', false, 'mensagem', 'Assinatura SaaS não encontrada para a instituição.');
    END IF;

    IF v_ass.estado = 'cancelada' THEN
        RETURN jsonb_build_object('sucesso', false, 'mensagem', 'A assinatura da instituição encontra-se cancelada.');
    END IF;

    -- Contagem de faturas que ultrapassam o corte
    SELECT COUNT(*) INTO v_faturas_corte_count
    FROM public.sige_saas_faturas f
    WHERE f.instituicao_id = p_instituicao_id
      AND f.estado IN ('aberta', 'paga_parcial', 'em_atraso')
      AND (v_hoje >= (public.data_limite_efectiva(f.id) + v_ass.dias_tolerancia + v_ass.dias_ate_suspensao)
           OR (v_ass.data_bloqueio_manual IS NOT NULL AND v_hoje >= v_ass.data_bloqueio_manual));

    -- Caso A: Pedido de reactivação automática mas possui faturas em corte
    IF p_acao_desejada = 'auto_reactivar' AND v_faturas_corte_count > 0 THEN
        RETURN jsonb_build_object(
            'sucesso', false,
            'mensagem', 'Não é possível reactivar automaticamente: a instituição possui faturas em atraso que excederam o prazo de corte (' || v_ass.dias_ate_suspensao || ' dias). Regularize ou use Reactivar Manualmente.'
        );
    END IF;

    -- Caso B: Pedido de suspensão automática mas não possui faturas em corte
    IF p_acao_desejada = 'auto_suspender' AND v_faturas_corte_count = 0 THEN
        RETURN jsonb_build_object(
            'sucesso', false,
            'mensagem', 'A instituição não possui faturas que excedam o prazo de corte (' || v_ass.dias_ate_suspensao || ' dias). O corte automático não se aplica. Para suspender administrativamente, utilize Suspender Manualmente.'
        );
    END IF;

    -- Determinar novo estado automático
    IF v_faturas_corte_count > 0 THEN
        v_novo_estado := 'suspensa';
        v_novo_status_escola := 'SUSPENSA';
        v_accao_log := 'SUSPENSAO_AUTOMATICA';
        v_motivo := 'Suspensão automática aplicada: ultrapassou o limite de corte de ' || v_ass.dias_ate_suspensao || ' dias.';
    ELSE
        -- Verificar faturas abertas
        SELECT COUNT(*) INTO v_faturas_abertas_count
        FROM public.sige_saas_faturas f
        WHERE f.instituicao_id = p_instituicao_id AND f.estado IN ('aberta', 'paga_parcial', 'em_atraso');

        IF v_faturas_abertas_count > 0 THEN
            v_novo_estado := 'fatura_pendente';
        ELSE
            v_novo_estado := 'activa';
        END IF;

        v_novo_status_escola := 'ATIVA';
        v_accao_log := 'REACTIVACAO_AUTOMATICA';
        v_motivo := 'Reactivação automática por regularização e cumprimento das regras do sistema.';
    END IF;

    UPDATE public.sige_saas_assinaturas
    SET estado = v_novo_estado, updated_at = timezone('Africa/Maputo', now())
    WHERE id = v_ass.id;

    UPDATE public.sige_escolas
    SET status = v_novo_status_escola, bloqueada_manualmente = FALSE
    WHERE id = p_instituicao_id;

    INSERT INTO public.sige_saas_log_assinaturas (
        instituicao_id, assinatura_id, accao, estado_anterior, estado_novo,
        feito_por, motivo
    )
    VALUES (
        p_instituicao_id, v_ass.id, v_accao_log, v_ass.estado, v_novo_estado,
        COALESCE(p_utilizador, 'Super Admin'), v_motivo
    );

    RETURN jsonb_build_object(
        'sucesso', true,
        'mensagem', 'Operação automática concluída com êxito (' || v_novo_estado || ').',
        'estado_novo', v_novo_estado,
        'status_escola', v_novo_status_escola,
        'modo_controlo', 'automatico'
    );
END;
$$ LANGUAGE plpgsql;

-- 2. Actualizar actualizar_estados_assinaturas() para incluir reactivação automática contínua
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
    v_faturas_corte_count INT := 0;
    v_faturas_abertas_count INT := 0;
BEGIN
    PERFORM pg_advisory_xact_lock(849204922);

    -- 1. Processar multas e atrasos em faturas abertas
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
    END LOOP;

    -- 2. Avaliação de Suspensão Automática e Transições
    FOR v_fat IN
        SELECT f.*, a.dias_tolerancia, a.dias_ate_suspensao, a.data_bloqueio_manual,
               a.estado as ass_estado, e.bloqueada_manualmente
        FROM public.sige_saas_faturas f
        JOIN public.sige_saas_assinaturas a ON a.id = f.assinatura_id
        JOIN public.sige_escolas e ON e.id = f.instituicao_id
        WHERE f.estado IN ('aberta', 'paga_parcial', 'em_atraso')
          AND COALESCE(e.bloqueada_manualmente, FALSE) = FALSE
    LOOP
        v_data_efectiva := public.data_limite_efectiva(v_fat.id);
        v_limite_tolerancia := v_data_efectiva + v_fat.dias_tolerancia;
        v_limite_suspensao := v_limite_tolerancia + v_fat.dias_ate_suspensao;

        IF v_fat.ass_estado NOT IN ('cancelada') THEN
            v_novo_estado := v_fat.ass_estado;

            IF v_fat.data_bloqueio_manual IS NOT NULL AND v_hoje >= v_fat.data_bloqueio_manual THEN
                v_novo_estado := 'suspensa';
            ELSIF v_hoje >= v_limite_suspensao THEN
                v_novo_estado := 'suspensa';
            ELSIF v_hoje > v_limite_tolerancia THEN
                v_novo_estado := 'restrita';
            ELSIF v_hoje > v_data_efectiva THEN
                v_novo_estado := 'em_atraso';
            END IF;

            IF v_novo_estado != v_fat.ass_estado THEN
                UPDATE public.sige_saas_assinaturas
                SET estado = v_novo_estado, updated_at = timezone('Africa/Maputo', now())
                WHERE id = v_fat.assinatura_id;

                UPDATE public.sige_escolas
                SET status = CASE 
                    WHEN v_novo_estado = 'suspensa' THEN 'SUSPENSA'
                    WHEN v_novo_estado = 'cancelada' THEN 'EXPIRADA'
                    ELSE 'ATIVA'
                END,
                bloqueada_manualmente = FALSE
                WHERE id = v_fat.instituicao_id;

                INSERT INTO public.sige_saas_log_assinaturas (
                    instituicao_id, assinatura_id, fatura_id, accao,
                    estado_anterior, estado_novo, feito_por, motivo
                )
                VALUES (
                    v_fat.instituicao_id, v_fat.assinatura_id, v_fat.id,
                    CASE WHEN v_novo_estado = 'suspensa' THEN 'SUSPENSAO_AUTOMATICA' ELSE 'TRANSICAO_AUTOMATICA_ESTADO' END,
                    v_fat.ass_estado, v_novo_estado, 'sistema',
                    'Transição automática de estado por vencimento/tolerância (Hoje: ' || v_hoje || ')'
                );

                v_alteracoes := v_alteracoes + 1;
            END IF;
        END IF;
    END LOOP;

    -- 3. Reactivação Automática de Instituições Regularizadas (que estavam suspensas/restritas)
    FOR v_ass IN
        SELECT a.*, e.bloqueada_manualmente
        FROM public.sige_saas_assinaturas a
        JOIN public.sige_escolas e ON e.id = a.instituicao_id
        WHERE a.estado IN ('suspensa', 'restrita', 'em_atraso')
          AND a.estado != 'cancelada'
          AND COALESCE(e.bloqueada_manualmente, FALSE) = FALSE
    LOOP
        SELECT COUNT(*) INTO v_faturas_corte_count
        FROM public.sige_saas_faturas f
        WHERE f.assinatura_id = v_ass.id
          AND f.estado IN ('aberta', 'paga_parcial', 'em_atraso')
          AND (v_hoje >= (public.data_limite_efectiva(f.id) + v_ass.dias_tolerancia + v_ass.dias_ate_suspensao)
               OR (v_ass.data_bloqueio_manual IS NOT NULL AND v_hoje >= v_ass.data_bloqueio_manual));

        IF v_faturas_corte_count = 0 THEN
            SELECT COUNT(*) INTO v_faturas_abertas_count
            FROM public.sige_saas_faturas f
            WHERE f.assinatura_id = v_ass.id AND f.estado IN ('aberta', 'paga_parcial');

            v_novo_estado := CASE WHEN v_faturas_abertas_count > 0 THEN 'fatura_pendente' ELSE 'activa' END;

            IF v_novo_estado != v_ass.estado THEN
                UPDATE public.sige_saas_assinaturas
                SET estado = v_novo_estado, updated_at = timezone('Africa/Maputo', now())
                WHERE id = v_ass.id;

                UPDATE public.sige_escolas
                SET status = 'ATIVA', bloqueada_manualmente = FALSE
                WHERE id = v_ass.instituicao_id;

                INSERT INTO public.sige_saas_log_assinaturas (
                    instituicao_id, assinatura_id, accao,
                    estado_anterior, estado_novo, feito_por, motivo
                )
                VALUES (
                    v_ass.instituicao_id, v_ass.id, 'REACTIVACAO_AUTOMATICA',
                    v_ass.estado, v_novo_estado, 'sistema',
                    'Reactivação automática por quitação/regularização de faturas'
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
