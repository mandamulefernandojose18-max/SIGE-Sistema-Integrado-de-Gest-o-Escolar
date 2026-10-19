/**
 * SIGE - PAINEL-ESCOLA | Classes, Níveis & Regime de Exame
 * Ficheiro de código independente do menu: classes-exames.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */

// ==================== GESTÃO DE CLASSES E NÍVEIS (COM / SEM EXAME) ====================

window.carregarClassesExames = async function(forcar = false) {
  if (typeof window.carregarPaginaClassesExames === 'function') {
    return await window.carregarPaginaClassesExames(forcar);
  }
};

// Auto-inicialização quando a view é aberta diretamente
document.addEventListener('DOMContentLoaded', () => {
  const viewEl = document.getElementById('view-classes-exames');
  if (viewEl && viewEl.style.display !== 'none') {
    window.carregarClassesExames();
  }
});
