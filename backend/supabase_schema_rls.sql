-- =====================================================
-- SIGE: Políticas de Segurança e RLS para o Supabase
-- =====================================================

ALTER TABLE public.sige_alunos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_professores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_turmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_disciplinas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_notas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_pautas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_pagamentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_assinaturas_escolas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_documentos_salvos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_logs_impressao ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_logs_acesso ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_permissoes_edicao_notas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_professor_disciplina_turma ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_content_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_admin_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_permission ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_usuarios_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_usuarios_user_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_escolas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_planos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_certificados ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_material_escolar ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sige_usuarios ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_all_sige_alunos" ON public.sige_alunos;
CREATE POLICY "service_all_sige_alunos" ON public.sige_alunos
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_professores" ON public.sige_professores;
CREATE POLICY "service_all_sige_professores" ON public.sige_professores
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_turmas" ON public.sige_turmas;
CREATE POLICY "service_all_sige_turmas" ON public.sige_turmas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_disciplinas" ON public.sige_disciplinas;
CREATE POLICY "service_all_sige_disciplinas" ON public.sige_disciplinas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_notas" ON public.sige_notas;
CREATE POLICY "service_all_sige_notas" ON public.sige_notas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_pautas" ON public.sige_pautas;
CREATE POLICY "service_all_sige_pautas" ON public.sige_pautas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_pagamentos" ON public.sige_pagamentos;
CREATE POLICY "service_all_sige_pagamentos" ON public.sige_pagamentos
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas;
CREATE POLICY "service_all_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_documentos_salvos" ON public.sige_documentos_salvos;
CREATE POLICY "service_all_sige_documentos_salvos" ON public.sige_documentos_salvos
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_logs_impressao" ON public.sige_logs_impressao;
CREATE POLICY "service_all_sige_logs_impressao" ON public.sige_logs_impressao
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_logs_acesso" ON public.sige_logs_acesso;
CREATE POLICY "service_all_sige_logs_acesso" ON public.sige_logs_acesso
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas;
CREATE POLICY "service_all_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma;
CREATE POLICY "service_all_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_django_session" ON public.django_session;
CREATE POLICY "service_all_django_session" ON public.django_session
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_django_migrations" ON public.django_migrations;
CREATE POLICY "service_all_django_migrations" ON public.django_migrations
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_django_content_type" ON public.django_content_type;
CREATE POLICY "service_all_django_content_type" ON public.django_content_type
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_django_admin_log" ON public.django_admin_log;
CREATE POLICY "service_all_django_admin_log" ON public.django_admin_log
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_auth_group" ON public.auth_group;
CREATE POLICY "service_all_auth_group" ON public.auth_group
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_auth_group_permissions" ON public.auth_group_permissions;
CREATE POLICY "service_all_auth_group_permissions" ON public.auth_group_permissions
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_auth_permission" ON public.auth_permission;
CREATE POLICY "service_all_auth_permission" ON public.auth_permission
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_usuarios_groups" ON public.sige_usuarios_groups;
CREATE POLICY "service_all_sige_usuarios_groups" ON public.sige_usuarios_groups
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_usuarios_user_permissions" ON public.sige_usuarios_user_permissions;
CREATE POLICY "service_all_sige_usuarios_user_permissions" ON public.sige_usuarios_user_permissions
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_escolas" ON public.sige_escolas;
CREATE POLICY "service_all_sige_escolas" ON public.sige_escolas
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_planos" ON public.sige_planos;
CREATE POLICY "service_all_sige_planos" ON public.sige_planos
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_certificados" ON public.sige_certificados;
CREATE POLICY "service_all_sige_certificados" ON public.sige_certificados
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_material_escolar" ON public.sige_material_escolar;
CREATE POLICY "service_all_sige_material_escolar" ON public.sige_material_escolar
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


DROP POLICY IF EXISTS "service_all_sige_usuarios" ON public.sige_usuarios;
CREATE POLICY "service_all_sige_usuarios" ON public.sige_usuarios
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );


-- Catálogo de Planos (Leitura Pública)
DROP POLICY IF EXISTS "public_read_planos" ON public.sige_planos;
CREATE POLICY "public_read_planos" ON public.sige_planos
    FOR SELECT USING (true);

-- Escolas Ativas (Leitura Pública de Informações Institucionais)
DROP POLICY IF EXISTS "public_read_escolas" ON public.sige_escolas;
CREATE POLICY "public_read_escolas" ON public.sige_escolas
    FOR SELECT USING (status = 'ATIVA');

-- Validação Pública de Certificados e Diplomas com QR Code
DROP POLICY IF EXISTS "public_read_certificados" ON public.sige_certificados;
CREATE POLICY "public_read_certificados" ON public.sige_certificados
    FOR SELECT USING (true);

-- Catálogo de Materiais Escolares e Livros
DROP POLICY IF EXISTS "public_read_material_escolar" ON public.sige_material_escolar;
CREATE POLICY "public_read_material_escolar" ON public.sige_material_escolar
    FOR SELECT USING (true);


-- Isolamento Multi-Tenant: sige_alunos
DROP POLICY IF EXISTS "tenant_select_sige_alunos" ON public.sige_alunos;
CREATE POLICY "tenant_select_sige_alunos" ON public.sige_alunos
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_alunos" ON public.sige_alunos;
CREATE POLICY "tenant_insert_sige_alunos" ON public.sige_alunos
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_alunos" ON public.sige_alunos;
CREATE POLICY "tenant_update_sige_alunos" ON public.sige_alunos
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_alunos" ON public.sige_alunos;
CREATE POLICY "tenant_delete_sige_alunos" ON public.sige_alunos
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_professores
DROP POLICY IF EXISTS "tenant_select_sige_professores" ON public.sige_professores;
CREATE POLICY "tenant_select_sige_professores" ON public.sige_professores
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_professores" ON public.sige_professores;
CREATE POLICY "tenant_insert_sige_professores" ON public.sige_professores
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_professores" ON public.sige_professores;
CREATE POLICY "tenant_update_sige_professores" ON public.sige_professores
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_professores" ON public.sige_professores;
CREATE POLICY "tenant_delete_sige_professores" ON public.sige_professores
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_turmas
DROP POLICY IF EXISTS "tenant_select_sige_turmas" ON public.sige_turmas;
CREATE POLICY "tenant_select_sige_turmas" ON public.sige_turmas
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_turmas" ON public.sige_turmas;
CREATE POLICY "tenant_insert_sige_turmas" ON public.sige_turmas
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_turmas" ON public.sige_turmas;
CREATE POLICY "tenant_update_sige_turmas" ON public.sige_turmas
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_turmas" ON public.sige_turmas;
CREATE POLICY "tenant_delete_sige_turmas" ON public.sige_turmas
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_disciplinas
DROP POLICY IF EXISTS "tenant_select_sige_disciplinas" ON public.sige_disciplinas;
CREATE POLICY "tenant_select_sige_disciplinas" ON public.sige_disciplinas
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_disciplinas" ON public.sige_disciplinas;
CREATE POLICY "tenant_insert_sige_disciplinas" ON public.sige_disciplinas
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_disciplinas" ON public.sige_disciplinas;
CREATE POLICY "tenant_update_sige_disciplinas" ON public.sige_disciplinas
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_disciplinas" ON public.sige_disciplinas;
CREATE POLICY "tenant_delete_sige_disciplinas" ON public.sige_disciplinas
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_notas
DROP POLICY IF EXISTS "tenant_select_sige_notas" ON public.sige_notas;
CREATE POLICY "tenant_select_sige_notas" ON public.sige_notas
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_notas" ON public.sige_notas;
CREATE POLICY "tenant_insert_sige_notas" ON public.sige_notas
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_notas" ON public.sige_notas;
CREATE POLICY "tenant_update_sige_notas" ON public.sige_notas
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_notas" ON public.sige_notas;
CREATE POLICY "tenant_delete_sige_notas" ON public.sige_notas
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_pautas
DROP POLICY IF EXISTS "tenant_select_sige_pautas" ON public.sige_pautas;
CREATE POLICY "tenant_select_sige_pautas" ON public.sige_pautas
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_pautas" ON public.sige_pautas;
CREATE POLICY "tenant_insert_sige_pautas" ON public.sige_pautas
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_pautas" ON public.sige_pautas;
CREATE POLICY "tenant_update_sige_pautas" ON public.sige_pautas
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_pautas" ON public.sige_pautas;
CREATE POLICY "tenant_delete_sige_pautas" ON public.sige_pautas
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_pagamentos
DROP POLICY IF EXISTS "tenant_select_sige_pagamentos" ON public.sige_pagamentos;
CREATE POLICY "tenant_select_sige_pagamentos" ON public.sige_pagamentos
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_pagamentos" ON public.sige_pagamentos;
CREATE POLICY "tenant_insert_sige_pagamentos" ON public.sige_pagamentos
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_pagamentos" ON public.sige_pagamentos;
CREATE POLICY "tenant_update_sige_pagamentos" ON public.sige_pagamentos
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_pagamentos" ON public.sige_pagamentos;
CREATE POLICY "tenant_delete_sige_pagamentos" ON public.sige_pagamentos
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_assinaturas_escolas
DROP POLICY IF EXISTS "tenant_select_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas;
CREATE POLICY "tenant_select_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas;
CREATE POLICY "tenant_insert_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas;
CREATE POLICY "tenant_update_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas;
CREATE POLICY "tenant_delete_sige_assinaturas_escolas" ON public.sige_assinaturas_escolas
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_documentos_salvos
DROP POLICY IF EXISTS "tenant_select_sige_documentos_salvos" ON public.sige_documentos_salvos;
CREATE POLICY "tenant_select_sige_documentos_salvos" ON public.sige_documentos_salvos
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_documentos_salvos" ON public.sige_documentos_salvos;
CREATE POLICY "tenant_insert_sige_documentos_salvos" ON public.sige_documentos_salvos
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_documentos_salvos" ON public.sige_documentos_salvos;
CREATE POLICY "tenant_update_sige_documentos_salvos" ON public.sige_documentos_salvos
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_documentos_salvos" ON public.sige_documentos_salvos;
CREATE POLICY "tenant_delete_sige_documentos_salvos" ON public.sige_documentos_salvos
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_logs_impressao
DROP POLICY IF EXISTS "tenant_select_sige_logs_impressao" ON public.sige_logs_impressao;
CREATE POLICY "tenant_select_sige_logs_impressao" ON public.sige_logs_impressao
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_logs_impressao" ON public.sige_logs_impressao;
CREATE POLICY "tenant_insert_sige_logs_impressao" ON public.sige_logs_impressao
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_logs_impressao" ON public.sige_logs_impressao;
CREATE POLICY "tenant_update_sige_logs_impressao" ON public.sige_logs_impressao
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_logs_impressao" ON public.sige_logs_impressao;
CREATE POLICY "tenant_delete_sige_logs_impressao" ON public.sige_logs_impressao
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_logs_acesso
DROP POLICY IF EXISTS "tenant_select_sige_logs_acesso" ON public.sige_logs_acesso;
CREATE POLICY "tenant_select_sige_logs_acesso" ON public.sige_logs_acesso
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_logs_acesso" ON public.sige_logs_acesso;
CREATE POLICY "tenant_insert_sige_logs_acesso" ON public.sige_logs_acesso
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_logs_acesso" ON public.sige_logs_acesso;
CREATE POLICY "tenant_update_sige_logs_acesso" ON public.sige_logs_acesso
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_logs_acesso" ON public.sige_logs_acesso;
CREATE POLICY "tenant_delete_sige_logs_acesso" ON public.sige_logs_acesso
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_permissoes_edicao_notas
DROP POLICY IF EXISTS "tenant_select_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas;
CREATE POLICY "tenant_select_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas;
CREATE POLICY "tenant_insert_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas;
CREATE POLICY "tenant_update_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas;
CREATE POLICY "tenant_delete_sige_permissoes_edicao_notas" ON public.sige_permissoes_edicao_notas
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Isolamento Multi-Tenant: sige_professor_disciplina_turma
DROP POLICY IF EXISTS "tenant_select_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma;
CREATE POLICY "tenant_select_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma;
CREATE POLICY "tenant_insert_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma;
CREATE POLICY "tenant_update_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma;
CREATE POLICY "tenant_delete_sige_professor_disciplina_turma" ON public.sige_professor_disciplina_turma
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );


-- Usuários: Leitura de membros da mesma escola ou SuperAdmin
DROP POLICY IF EXISTS "usuarios_tenant_select" ON public.sige_usuarios;
CREATE POLICY "usuarios_tenant_select" ON public.sige_usuarios
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );
