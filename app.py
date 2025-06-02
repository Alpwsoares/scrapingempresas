# app.py

from flask import Flask, render_template, request, send_file
import pandas as pd
import os
# IMPORTANTE: Importa a função de scraping que criamos no arquivo scraper.py
from scraper import scrape_guiamais

app = Flask(__name__)

# Rota principal para exibir o formulário HTML
@app.route('/')
def index():
    return render_template('index.html')

# Rota para processar a busca quando o formulário é enviado
@app.route('/buscar', methods=['POST'])
def buscar():
    # Pega os dados que o usuário digitou no formulário
    estado = request.form['estado']
    cidade = request.form['cidade']
    segmento = request.form['segmento']

    print(f"\n--- Requisição de Busca Recebida ---")
    print(f"Estado: {estado}, Cidade: {cidade}, Segmento: {segmento}")

    # CHAMADA PARA A FUNÇÃO DE WEB SCRAPING REAL
    try:
        # Chama a função scrape_guiamais do nosso scraper.py
        dados_empresas = scrape_guiamais(estado, cidade, segmento)
        
        if not dados_empresas:
            # Se nenhum dado for coletado (por exemplo, nenhum resultado ou todos filtrados por N/A),
            # criamos um DataFrame vazio ou com uma mensagem para o usuário.
            print("Nenhum dado de empresa coletado ou todos foram filtrados. Gerando planilha com aviso.")
            df = pd.DataFrame([
                {'Nome Fantasia': 'Nenhum dado encontrado',
                 'Endereço Completo': 'Verifique o segmento, cidade, estado ou tente outros termos.',
                 'Telefone': 'N/A'}
            ])
        else:
            # Converte a lista de dicionários (dados coletados) em um DataFrame do Pandas
            df = pd.DataFrame(dados_empresas)

        # Define o nome do arquivo para download
        # Normaliza o nome do arquivo para evitar caracteres especiais e espaços
        nome_arquivo = f"dados_coletados_{cidade.replace(' ', '_').replace('/', '_')}_{segmento.replace(' ', '_').replace('/', '_')}.xlsx"
        
        # Caminho completo para salvar o arquivo na pasta 'downloads'
        caminho_arquivo = os.path.join("downloads", nome_arquivo) 

        # Garante que a pasta 'downloads' exista
        os.makedirs('downloads', exist_ok=True)

        # Salva o DataFrame como um arquivo Excel (.xlsx)
        df.to_excel(caminho_arquivo, index=False) # index=False para não incluir o índice do DataFrame como coluna

        print(f"Planilha '{nome_arquivo}' gerada com sucesso e pronta para download.")
        # Retorna o arquivo para download
        return send_file(caminho_arquivo, as_attachment=True, download_name=nome_arquivo)

    except Exception as e:
        print(f"\nERRO INESPERADO DURANTE O PROCESSO DE SCRAPING OU GERAÇÃO DA PLANILHA: {e}")
        # Em caso de erro, podemos renderizar a página inicial novamente com uma mensagem de erro
        return render_template('index.html', error_message=f"Ocorreu um erro ao processar sua busca: {e}. Verifique o console para mais detalhes.")


if __name__ == '__main__':
    # Cria a pasta 'downloads' se ela não existir ao iniciar a aplicação
    os.makedirs('downloads', exist_ok=True)
    # Roda a aplicação Flask. debug=True permite que o servidor reinicie automaticamente
    # ao salvar alterações no código e mostra erros detalhados.
    app.run(debug=True)