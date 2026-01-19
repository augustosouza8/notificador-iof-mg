// Funções JavaScript para gerenciar formulários e interações

let termCount = 0;
let emailCount = 0;
const MAX_TERMS = 5;
const MAX_EMAILS = 5;

// ========== GERENCIAMENTO DE TERMOS ==========

function addSearchTerm(termValue = '', exactValue = false) {
    if (termCount >= MAX_TERMS) {
        alert(`Você pode adicionar no máximo ${MAX_TERMS} termos.`);
        return;
    }

    const container = document.getElementById('termsContainer');
    if (!container) return;

    const termDiv = document.createElement('div');
    termDiv.className = 'flex items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200';
    termDiv.dataset.termIndex = termCount;

    termDiv.innerHTML = `
        <input type="text" name="term" value="${escapeHtml(termValue)}" 
               placeholder="Digite o termo" required maxlength="255"
               class="flex-1 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <label class="flex items-center gap-2 cursor-pointer group relative">
            <input type="checkbox" name="term_exact" ${exactValue ? 'checked' : ''} 
                   class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500">
            <span class="text-sm text-gray-700">Exato</span>
            <div class="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-gray-800 text-white text-xs rounded py-2 px-3 w-64 z-10 shadow-lg whitespace-normal">
                <strong>Busca Exata:</strong> Encontra apenas o termo completo exatamente como escrito.<br><br>
                <strong>Busca Parcial:</strong> Encontra o termo mesmo como parte de outras palavras.
            </div>
            <i class="fas fa-info-circle text-blue-500 text-xs cursor-help" title="Busca Exata: encontra apenas o termo completo. Busca Parcial: encontra o termo mesmo como parte de outras palavras."></i>
        </label>
        <button type="button" onclick="removeSearchTerm(${termCount})" 
                class="text-red-600 hover:text-red-800 p-2 transition">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(termDiv);
    termCount++;

    updateTermButtons();
}

function removeSearchTerm(index) {
    const container = document.getElementById('termsContainer');
    if (!container) return;

    const termDiv = container.querySelector(`[data-term-index="${index}"]`);
    if (termDiv) {
        termDiv.remove();
        termCount--;
        updateTermButtons();
    }
}

function updateTermButtons() {
    const addBtn = document.getElementById('addTermBtn');
    const newTermInput = document.getElementById('newTerm');
    
    if (addBtn) {
        addBtn.disabled = termCount >= MAX_TERMS;
    }
    if (newTermInput) {
        newTermInput.disabled = termCount >= MAX_TERMS;
    }
}

// Event listener para adicionar termo
document.addEventListener('DOMContentLoaded', function() {
    const addTermBtn = document.getElementById('addTermBtn');
    const newTermInput = document.getElementById('newTerm');

    if (addTermBtn && newTermInput) {
        addTermBtn.addEventListener('click', function() {
            const termValue = newTermInput.value.trim();
            if (termValue) {
                addSearchTerm(termValue, false);
                newTermInput.value = '';
            }
        });

        newTermInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addTermBtn.click();
            }
        });
    }
});

// ========== GERENCIAMENTO DE EMAILS ==========

function addEmailField(emailValue = '') {
    if (emailCount >= MAX_EMAILS) {
        alert(`Você pode adicionar no máximo ${MAX_EMAILS} emails.`);
        return;
    }

    const container = document.getElementById('emailsContainer');
    if (!container) return;

    const emailDiv = document.createElement('div');
    emailDiv.className = 'flex items-center gap-2';
    emailDiv.dataset.emailIndex = emailCount;

    emailDiv.innerHTML = `
        <input type="email" name="mail_to" value="${escapeHtml(emailValue)}" 
               placeholder="email@exemplo.com" 
               class="flex-1 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <button type="button" onclick="removeEmailField(${emailCount})" 
                class="text-red-600 hover:text-red-800 p-2 transition">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(emailDiv);
    emailCount++;

    updateEmailButtons();
}

function removeEmailField(index) {
    const container = document.getElementById('emailsContainer');
    if (!container) return;

    const emailDiv = container.querySelector(`[data-email-index="${index}"]`);
    if (emailDiv) {
        emailDiv.remove();
        emailCount--;
        updateEmailButtons();
    }
}

function updateEmailButtons() {
    const addBtn = document.getElementById('addEmailBtn');
    
    if (addBtn) {
        addBtn.disabled = emailCount >= MAX_EMAILS;
    }
}

// Event listener para adicionar email
document.addEventListener('DOMContentLoaded', function() {
    const addEmailBtn = document.getElementById('addEmailBtn');
    
    if (addEmailBtn) {
        addEmailBtn.addEventListener('click', function() {
            addEmailField('');
        });
    }
});

// ========== VALIDAÇÃO DE FORMULÁRIO ==========

function validateForm() {
    const form = document.getElementById('configForm');
    if (!form) return true;

    // Validar termos
    const terms = form.querySelectorAll('input[name="term"]');
    let hasValidTerm = false;
    terms.forEach(term => {
        if (term.value.trim()) {
            hasValidTerm = true;
        }
    });

    if (!hasValidTerm) {
        alert('É necessário adicionar pelo menos um termo de busca.');
        return false;
    }

    if (terms.length > MAX_TERMS) {
        alert(`Máximo de ${MAX_TERMS} termos permitidos.`);
        return false;
    }

    // Validar emails
    const emails = form.querySelectorAll('input[name="mail_to"]');
    const emailValues = Array.from(emails).map(e => e.value.trim()).filter(e => e);
    
    if (emailValues.length > MAX_EMAILS) {
        alert(`Máximo de ${MAX_EMAILS} emails permitidos.`);
        return false;
    }

    // Validar formato de emails
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    for (const email of emailValues) {
        if (!emailRegex.test(email)) {
            alert(`Email inválido: ${email}`);
            return false;
        }
    }

    // Validar URL do Teams (se preenchida)
    const teamsWebhook = form.querySelector('#teams_webhook');
    if (teamsWebhook && teamsWebhook.value.trim()) {
        try {
            const url = new URL(teamsWebhook.value);
            if (url.protocol !== 'https:') {
                alert('O webhook do Teams deve ser uma URL HTTPS.');
                return false;
            }
        } catch (e) {
            alert('URL do webhook do Teams inválida.');
            return false;
        }
    }

    return true;
}

// Adicionar validação ao submit do formulário
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('configForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
        });
    }
});

// ========== UTILITÁRIOS ==========

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// ========== BACKTEST ==========

function executeBacktest(configId, date) {
    const executeBtn = document.getElementById('executeBtn');
    if (executeBtn) {
        executeBtn.disabled = true;
        executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Executando...';
    }

    // O backtest será executado via POST do formulário
    // Esta função pode ser usada para validação adicional se necessário
    return true;
}

document.addEventListener('DOMContentLoaded', function() {
    const backtestForm = document.getElementById('backtestForm');
    if (backtestForm) {
        backtestForm.addEventListener('submit', function(e) {
            const dateInput = document.getElementById('date');
            if (!dateInput || !dateInput.value) {
                e.preventDefault();
                alert('Por favor, selecione uma data.');
                return false;
            }
        });
    }
});
