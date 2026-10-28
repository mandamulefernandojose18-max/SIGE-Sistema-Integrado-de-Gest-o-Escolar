-- =====================================================================
-- SIGE: Migração de Pagamentos Adiantados e Periodicidade Editável SaaS
-- =====================================================================

CREATE OR REPLACE FUNCTION public.confirmar_pagamento(p_pagamento_id UUID, p_utilizador TEXT)
RETURNS JSONB AS $$
DECLARE
    v_pag RECORD;
    v_fat RECORD;
    v_ass RECORD;
    v_plano RECORD;
    v_outra_fat RECORD;
    v_faturas_atraso_restantes INT;
    v_novo_valor_pago NUMERIC(12,2);
    v_total_devido NUMERIC(12,2);
    v_devido_outra NUMERIC(12,2);
    v_sobra NUMERIC(12,2) := 0;
    v_fator NUMERIC(5,2) := 1.00;
    v_preco_efetivo NUMERIC(12,2);
    v_meses_adicionais INT := 0;
    v_dias_adicionais INT := 0;
    v_resto_sobra NUMERIC(12,2) := 0;
    v_base_extensao DATE;
    v_nova_proxima DATE;
    v_desc_adiantado TEXT := '';
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
    SELECT * INTO v_plano FROM public.sige_saas_planos WHERE id = v_ass.plano_id;

    v_total_devido := v_fat.valor + v_fat.multa_aplicada;
    v_novo_valor_pago := v_fat.valor_pago + v_pag.valor;

    -- Actualiza o pagamento
    UPDATE public.sige_saas_pagamentos
    SET estado = 'confirmado',
        confirmado_por = COALESCE(p_utilizador, 'Super Admin'),
        confirmado_em = timezone('Africa/Maputo', now()),
        updated_at = timezone('Africa/Maputo', now())
    WHERE id = p_pagamento_id;

    -- Actualiza a fatura principal
    IF v_novo_valor_pago >= v_total_devido THEN
        v_sobra := v_novo_valor_pago - v_total_devido;
        UPDATE public.sige_saas_faturas
        SET valor_pago = v_total_devido,
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

    -- 1. Abater excedente em outras faturas pendentes da mesma instituição
    IF v_sobra > 0 THEN
        FOR v_outra_fat IN
            SELECT * FROM public.sige_saas_faturas
            WHERE instituicao_id = v_ass.instituicao_id AND estado IN ('aberta', 'paga_parcial', 'em_atraso') AND id != v_fat.id
            ORDER BY periodo_inicio ASC
        LOOP
            EXIT WHEN v_sobra <= 0;
            v_devido_outra := (v_outra_fat.valor + v_outra_fat.multa_aplicada) - v_outra_fat.valor_pago;
            IF v_sobra >= v_devido_outra THEN
                UPDATE public.sige_saas_faturas
                SET valor_pago = (valor + multa_aplicada), estado = 'paga', updated_at = timezone('Africa/Maputo', now())
                WHERE id = v_outra_fat.id;
                v_sobra := v_sobra - v_devido_outra;
            ELSE
                UPDATE public.sige_saas_faturas
                SET valor_pago = valor_pago + v_sobra, estado = 'paga_parcial', updated_at = timezone('Africa/Maputo', now())
                WHERE id = v_outra_fat.id;
                v_sobra := 0;
            END IF;
        END LOOP;
    END IF;

    -- 2. Havendo sobra remanescente, calcular tempo adiantado correspondente e estender proxima_fatura_em
    IF v_sobra > 0 AND v_plano.preco_mensal > 0 THEN
        v_fator := CASE
            WHEN v_ass.periodicidade = 'trimestral' THEN 0.95
            WHEN v_ass.periodicidade = 'semestral' THEN 0.90
            WHEN v_ass.periodicidade = 'anual' THEN 0.85
            ELSE 1.00
        END;
        v_preco_efetivo := v_plano.preco_mensal * v_fator;
        v_meses_adicionais := FLOOR(v_sobra / v_preco_efetivo)::INT;
        v_resto_sobra := v_sobra - (v_meses_adicionais * v_preco_efetivo);
        v_dias_adicionais := ROUND(v_resto_sobra / (v_preco_efetivo / 30.0))::INT;

        IF v_dias_adicionais >= 30 THEN
            v_meses_adicionais := v_meses_adicionais + (v_dias_adicionais / 30);
            v_dias_adicionais := v_dias_adicionais % 30;
        END IF;

        v_base_extensao := GREATEST(v_ass.proxima_fatura_em, v_fat.periodo_fim);
        v_nova_proxima := (v_base_extensao + (v_meses_adicionais || ' months')::INTERVAL + (v_dias_adicionais || ' days')::INTERVAL)::DATE;

        UPDATE public.sige_saas_assinaturas
        SET proxima_fatura_em = v_nova_proxima, updated_at = timezone('Africa/Maputo', now())
        WHERE id = v_ass.id;

        v_desc_adiantado := ' Adiantamento de ' || v_sobra || ' MZN corresponde a ' || v_meses_adicionais || ' mês(es) e ' || v_dias_adicionais || ' dia(s) adicionais (prorrogado até ' || TO_CHAR(v_nova_proxima, 'DD/MM/YYYY') || ').';
    END IF;

    -- 3. Verificar faturas em atraso restantes
    SELECT COUNT(*) INTO v_faturas_atraso_restantes
    FROM public.sige_saas_faturas
    WHERE instituicao_id = v_pag.instituicao_id AND estado IN ('em_atraso', 'aberta');

    -- Reactivação automática se não restarem débitos pendentes
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
        'Confirmação de pagamento Ref: ' || v_pag.referencia || ' no valor de ' || v_pag.valor || ' MZN.' || v_desc_adiantado
    );

    RETURN jsonb_build_object(
        'sucesso', true,
        'mensagem', 'Pagamento confirmado com sucesso.',
        'fatura_estado', (CASE WHEN v_novo_valor_pago >= v_total_devido THEN 'paga' ELSE 'paga_parcial' END),
        'assinatura_reativada', (v_faturas_atraso_restantes = 0),
        'valor_excedente', v_sobra,
        'meses_adicionais', v_meses_adicionais,
        'dias_adicionais', v_dias_adicionais,
        'nova_proxima_fatura', v_nova_proxima
    );
END;
$$ LANGUAGE plpgsql;
