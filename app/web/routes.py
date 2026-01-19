"""Rotas web para interface HTML."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.services.search_service import SearchService
from search.source import SearchSource, Term, Trigger
from iof.v1.consulta import consulta_por_data, convert_pages
from mailer.mailer import Mailer
from mailer.notification import notification_email

bp = Blueprint('web', __name__)


@bp.route('/')
def index():
    """Lista todas as configurações."""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    configs = SearchService.list_configs(active_only=active_only)
    return render_template('index.html', configs=configs, active_only=active_only)


@bp.route('/configs/new', methods=['GET', 'POST'])
def create_config():
    """Criar nova configuração."""
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # Processar termos
        terms = []
        term_inputs = request.form.getlist('term')
        exact_inputs = request.form.getlist('term_exact')
        
        for i, term_text in enumerate(term_inputs):
            if term_text.strip():
                terms.append({
                    'term': term_text.strip(),
                    'exact': exact_inputs[i] == 'on' if i < len(exact_inputs) else True
                })
        
        # Processar emails
        mail_to = [email.strip() for email in request.form.getlist('mail_to') if email.strip()]
        
        # Montar dados da configuração
        config_data = {
            'label': data.get('label', '').strip(),
            'description': data.get('description', '').strip(),
            'attach_csv': data.get('attach_csv') == 'on',
            'mail_to': mail_to,
            'mail_subject': data.get('mail_subject', '').strip(),
            'teams_webhook': None,  # Teams removido da interface
            'terms': terms,
            'active': True
        }
        
        # Validação básica
        errors = {}
        if not config_data['label']:
            errors['label'] = 'Nome é obrigatório'
        if len(terms) == 0:
            errors['terms'] = 'É necessário adicionar pelo menos um termo'
        if len(terms) > 5:
            errors['terms'] = 'Máximo de 5 termos permitidos'
        if len(mail_to) > 5:
            errors['mail_to'] = 'Máximo de 5 emails permitidos'
        
        if errors:
            return render_template('create.html', errors=errors, form_data=config_data)
        
        try:
            config = SearchService.save_config(config_data)
            flash('Configuração criada com sucesso!', 'success')
            return redirect(url_for('web.detail_config', config_id=config.id))
        except Exception as e:
            flash(f'Erro ao criar configuração: {str(e)}', 'error')
            return render_template('create.html', errors={}, form_data=config_data)
    
    return render_template('create.html', errors={}, form_data={})


@bp.route('/configs/<int:config_id>')
def detail_config(config_id):
    """Visualizar detalhes de uma configuração."""
    config = SearchService.get_config(config_id)
    if not config:
        flash('Configuração não encontrada', 'error')
        return redirect(url_for('web.index'))
    
    return render_template('detail.html', config=config)


@bp.route('/configs/<int:config_id>/edit', methods=['GET', 'POST'])
def edit_config(config_id):
    """Editar configuração."""
    config = SearchService.get_config(config_id)
    if not config:
        flash('Configuração não encontrada', 'error')
        return redirect(url_for('web.index'))
    
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # Processar termos
        terms = []
        term_inputs = request.form.getlist('term')
        exact_inputs = request.form.getlist('term_exact')
        
        for i, term_text in enumerate(term_inputs):
            if term_text.strip():
                terms.append({
                    'term': term_text.strip(),
                    'exact': exact_inputs[i] == 'on' if i < len(exact_inputs) else True
                })
        
        # Processar emails
        mail_to = [email.strip() for email in request.form.getlist('mail_to') if email.strip()]
        
        # Montar dados da configuração
        config_data = {
            'label': data.get('label', '').strip(),
            'description': data.get('description', '').strip(),
            'attach_csv': data.get('attach_csv') == 'on',
            'mail_to': mail_to,
            'mail_subject': data.get('mail_subject', '').strip(),
            'teams_webhook': None,  # Teams removido da interface
            'terms': terms,
            'active': data.get('active') == 'on'
        }
        
        # Validação básica
        errors = {}
        if not config_data['label']:
            errors['label'] = 'Nome é obrigatório'
        if len(terms) == 0:
            errors['terms'] = 'É necessário adicionar pelo menos um termo'
        if len(terms) > 5:
            errors['terms'] = 'Máximo de 5 termos permitidos'
        if len(mail_to) > 5:
            errors['mail_to'] = 'Máximo de 5 emails permitidos'
        
        if errors:
            return render_template('edit.html', config=config, errors=errors, form_data=config_data)
        
        try:
            updated_config = SearchService.update_config(config_id, config_data)
            if updated_config:
                flash('Configuração atualizada com sucesso!', 'success')
                return redirect(url_for('web.detail_config', config_id=config_id))
            else:
                flash('Erro ao atualizar configuração', 'error')
        except Exception as e:
            flash(f'Erro ao atualizar configuração: {str(e)}', 'error')
    
    # Preparar dados do formulário
    form_data = {
        'label': config.label,
        'description': config.description,
        'attach_csv': config.attach_csv,
        'mail_to': config.mail_to,
        'mail_subject': config.mail_subject,
        'teams_webhook': '',  # Teams removido da interface
        'terms': [{'term': t.term, 'exact': t.exact} for t in config.terms],
        'active': config.active
    }
    
    return render_template('edit.html', config=config, errors={}, form_data=form_data)


@bp.route('/configs/<int:config_id>/delete', methods=['POST'])
def delete_config(config_id):
    """Deletar configuração."""
    deleted = SearchService.delete_config(config_id)
    if deleted:
        flash('Configuração deletada com sucesso!', 'success')
    else:
        flash('Configuração não encontrada', 'error')
    return redirect(url_for('web.index'))


@bp.route('/configs/<int:config_id>/backtest', methods=['GET', 'POST'])
def backtest_config(config_id):
    """Página de backtest."""
    config = SearchService.get_config(config_id)
    if not config:
        flash('Configuração não encontrada', 'error')
        return redirect(url_for('web.index'))
    
    # Verificar se backtest está habilitado
    import os
    app_env = os.getenv('APP_ENV', 'development')
    if app_env != 'development':
        flash('Backtest disponível apenas em ambiente de desenvolvimento', 'error')
        return redirect(url_for('web.detail_config', config_id=config_id))
    
    if request.method == 'POST':
        date_str = request.form.get('date')
        if not date_str:
            flash('Data é obrigatória', 'error')
            today = date.today()
            return render_template('backtest.html', config=config, result=None, test_date=None, max_date=today.isoformat())
        
        try:
            test_date = date.fromisoformat(date_str)
        except ValueError:
            flash('Data inválida. Use o formato YYYY-MM-DD', 'error')
            today = date.today()
            return render_template('backtest.html', config=config, result=None, test_date=None, max_date=today.isoformat())
        
        if test_date > date.today():
            flash('Não é possível testar datas futuras', 'error')
            today = date.today()
            return render_template('backtest.html', config=config, result=None, test_date=None, max_date=today.isoformat())
        
        # Inicializar source de busca
        diarios_dir = current_app.config.get('DIARIOS_DIR', 'diarios')
        import os
        os.makedirs(diarios_dir, exist_ok=True)
        search_db = os.path.join(diarios_dir, 'diarios.db')
        source = SearchSource(search_db)
        
        try:
            # Verificar se já tem páginas importadas
            has_pages = source.has_pages(test_date)
            
            if not has_pages:
                # Baixar e importar diário
                try:
                    response = consulta_por_data(test_date)
                    arquivo = response.dados.arquivo_caderno_principal.arquivo
                    paginas_iof = convert_pages(arquivo, test_date)
                    # Converter para Pagina do search
                    from search.source import Pagina as SearchPagina
                    paginas = [
                        SearchPagina(
                            titulo="",
                            num_pagina=p.num_pagina,
                            descricao="",
                            conteudo=p.conteudo,
                            data_publicacao=p.data_publicacao
                        )
                        for p in paginas_iof
                    ]
                    source.import_pages(paginas)
                    flash(f'Diário de {test_date} baixado e importado com sucesso', 'success')
                except Exception as e:
                    source.close()
                    error_msg = str(e).lower()
                    if 'not found' in error_msg or '404' in error_msg:
                        flash(f'Diário não encontrado para {test_date}', 'error')
                    else:
                        flash(f'Erro ao baixar diário: {str(e)}', 'error')
                    today = date.today()
                    return render_template('backtest.html', config=config, result=None, test_date=None, max_date=today.isoformat())
            
            # Converter termos da config para Term do search
            search_terms = [
                Term(term=term.term, exact=term.exact)
                for term in config.terms
            ]
            
            # Executar busca
            report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
            
            # Converter report para dicionário
            result = {
                'publish_date': report.publish_date.isoformat(),
                'highlights': [
                    {
                        'page': h.page,
                        'content': h.content,
                        'term': h.term,
                        'page_url': h.page_url
                    }
                    for h in report.highlights
                ],
                'search_terms': [
                    {
                        'term': t.term,
                        'exact': t.exact
                    }
                    for t in report.search_terms
                ],
                'trigger': report.trigger.value,
                'count': report.count
            }
            
            # Enviar email se houver resultados e emails configurados
            if report.count > 0 and config.mail_to:
                # Verificar se as configurações de email estão definidas
                mail_server = current_app.config.get('MAIL_SERVER', '')
                mail_port = current_app.config.get('MAIL_PORT', 0)
                mail_use_tls = current_app.config.get('MAIL_USE_TLS', False)
                mail_username = current_app.config.get('MAIL_USERNAME', '')
                
                if not mail_server:
                    flash('Configurações de email não estão definidas. Configure MAIL_SMTP_HOST no arquivo .env para enviar emails. Para desenvolvimento local, você pode usar MailHog (porta 1025) ou configurar um servidor SMTP real (Gmail, SendGrid, etc.).', 'warning')
                elif not mail_username:
                    flash('MAIL_SMTP_USER não está configurado. Configure no arquivo .env para enviar emails.', 'warning')
                else:
                    try:
                        mailer = Mailer(current_app)
                        subject = config.mail_subject or "Teste de Busca - Diário Oficial"
                        email = notification_email(config.mail_to, report, subject=subject)
                        mailer.send(email)
                        flash(f'Email de teste enviado com sucesso para {len(config.mail_to)} destinatário(s)!', 'success')
                    except (ConnectionRefusedError, OSError) as e:
                        error_code = getattr(e, 'errno', None)
                        if error_code == 61 or 'Connection refused' in str(e) or '[Errno 61]' in str(e):
                            tls_hint = f' Verifique também se MAIL_USE_TLS está configurado corretamente (para Gmail na porta 587, deve ser true).' if 'gmail' in mail_server.lower() else ''
                            flash(f'Erro ao conectar ao servidor SMTP ({mail_server}:{mail_port}). O servidor não está acessível ou não está rodando.{tls_hint} Verifique: 1) Se o servidor SMTP está acessível, 2) Se as configurações MAIL_SMTP_HOST e MAIL_SMTP_PORT estão corretas no arquivo .env, 3) Se há firewall bloqueando a conexão.', 'error')
                        else:
                            flash(f'Erro de conexão com o servidor SMTP: {str(e)}', 'error')
                    except Exception as e:
                        error_msg = str(e)
                        if 'authentication' in error_msg.lower() or 'login' in error_msg.lower() or '535' in error_msg:
                            flash(f'Erro de autenticação no servidor SMTP. Verifique se MAIL_SMTP_USER e MAIL_SMTP_PASSWORD estão corretos no arquivo .env. Para Gmail, certifique-se de usar uma "Senha de App" e não sua senha normal.', 'error')
                        elif 'timeout' in error_msg.lower():
                            flash(f'Timeout ao conectar ao servidor SMTP ({mail_server}:{mail_port}). Verifique se o servidor está acessível e sua conexão com a internet.', 'error')
                        else:
                            flash(f'Erro ao enviar email: {error_msg}. Verifique as configurações de email no arquivo .env.', 'error')
            
            today = date.today()
            return render_template('backtest.html', config=config, result=result, test_date=test_date, max_date=today.isoformat())
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'Erro ao executar backtest: {str(e)}', 'error')
            today = date.today()
            return render_template('backtest.html', config=config, result=None, test_date=None, max_date=today.isoformat())
        finally:
            source.close()
    
    today = date.today()
    return render_template('backtest.html', config=config, result=None, test_date=None, max_date=today.isoformat())
