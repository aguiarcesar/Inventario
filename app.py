from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import re

app = Flask(__name__)
app.secret_key = "chave_secreta_para_alertas"  # Necessário para usar flash messages
NOME_BANCO = "banco_estoque.db"

# ==============================================================================
# CONFIGURAÇÃO E INICIALIZAÇÃO DO BANCO DE DADOS
# ==============================================================================
def obter_conexao():
    conn = sqlite3.connect(NOME_BANCO)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
    return conn

def inicializar_banco():
    """Garante que as tabelas necessárias existam no servidor (Evita Erro 500)"""
    conn = obter_conexao()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            sku TEXT PRIMARY KEY,
            ean TEXT UNIQUE,
            descricao TEXT,
            localizacao TEXT,
            quantidade INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Executa a criação da tabela assim que a aplicação sobe no Render
inicializar_banco()


# ==============================================================================
# VALIDATÓRIOS
# ==============================================================================
# Validador de formato SKU (5 dígitos - hífen - 10 dígitos)
def validar_sku(sku):
    padrao = r'^\d{5}-\d{10}$'
    return bool(re.match(padrao, sku))

# Validador de EAN (Apenas 13 dígitos numéricos)
def validar_ean(ean):
    return ean.isdigit() and len(ean) == 13


# ==============================================================================
# 1. ROTA PRINCIPAL: REDIRECIONA DIRETO PARA O INVENTÁRIO (FOCO DO CLIENTE)
# ==============================================================================
@app.route('/')
def index():
    return redirect(url_for('inventario'))


# ==============================================================================
# 2. MANTER TELA E REGISTRO DE CADASTRO ATIVOS
# ==============================================================================
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'GET':
        return render_template('cadastrar.html')

    # Processamento do formulário (POST)
    sku = request.form.get('sku', '').strip()
    ean = request.form.get('ean', '').strip()
    descricao = request.form.get('descricao', '').strip()
    localizacao = request.form.get('localizacao', '').strip()
    qtd_inicial = int(request.form.get('quantidade_inicial', 0))

    # Validações de formato e integridade
    if not validar_sku(sku):
        flash("SKU inválido! Deve seguir o padrão de 16 dígitos (Ex: 12345-1234567890).", "danger")
        return redirect(url_for('cadastrar'))

    if not validar_ean(ean):
        flash("Código de barras (EAN) inválido! Deve conter exatamente 13 dígitos numéricos.", "danger")
        return redirect(url_for('cadastrar'))

    if not descricao or len(descricao) > 90:
        flash("A descrição é obrigatória e deve ter no máximo 90 caracteres.", "danger")
        return redirect(url_for('cadastrar'))

    conn = obter_conexao()
    try:
        conn.execute('''
            INSERT INTO produtos (sku, ean, descricao, localizacao, quantidade)
            VALUES (?, ?, ?, ?, ?)
        ''', (sku, ean, descricao, localizacao, qtd_inicial))
        conn.commit()
        flash("Novo produto cadastrado com sucesso!", "success")
    except sqlite3.IntegrityError:
        flash("Erro: Já existe um produto cadastrado com este SKU ou Código de barras (EAN).", "danger")
    finally:
        conn.close()

    return redirect(url_for('cadastrar'))


# ==============================================================================
# 3. MANTER ROTAS DO INVENTÁRIO E DA API DE BIPAGEM ATIVAS
# ==============================================================================
@app.route('/inventario')
def inventario():
    return render_template('inventario.html')

@app.route('/api/inventariar_item')
def inventariar_item():
    termo = request.args.get('q', '').strip()
    if not termo:
        return jsonify({'erro': 'Código vazio'}), 400

    conn = obter_conexao()
    # Busca o produto para garantir que o EAN/SKU bipado é válido no sistema
    produto = conn.execute(
        'SELECT sku, ean, descricao FROM produtos WHERE ean = ? OR sku = ?', 
        (termo, termo)
    ).fetchone()
    conn.close()

    if produto:
        return jsonify({
            'sucesso': True,
            'sku': produto['sku'],
            'ean': produto['ean'],
            'descricao': produto['descricao']
        })
    else:
        return jsonify({'sucesso': False, 'erro': 'Produto não cadastrado'}), 404


# ==============================================================================
# 4. DESATIVADO / OCULTO PARA A VERSÃO DE TESTE DO CLIENTE
# ==============================================================================
# @app.route('/movimentar', methods=['GET', 'POST'])
# def movimentar():
#      return "Módulo não disponível na versão de demonstração."

# @app.route('/api/buscar_produto')
# def buscar_produto():
#      return jsonify([])


if __name__ == '__main__':
    # Configuração ideal para desenvolvimento local e aceitação de redes externas
    app.run(host='0.0.0.0', port=5000, debug=True)
