# scraper.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementNotInteractableException

from bs4 import BeautifulSoup
import time
import random
import urllib.parse
import pandas as pd

# --- FUNÇÃO PRINCIPAL DE SCRAPING ---
def scrape_guiamais(estado, cidade, segmento):
    """
    Coleta dados de empresas do GuiaMais.com.br, priorizando WhatsApp, depois botão Ligar.
    Filtra empresas sem Nome Fantasia e permite salvar em XLSX.
    """
    dados_coletados = []
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Comente esta linha para ver o navegador em ação
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('window-size=1920x1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        print("WebDriver inicializado com sucesso.")

        pagina = 1
        limite_paginas = 3 
        
        segmento_codificado = urllib.parse.quote(segmento)
        cidade_estado_codificado = urllib.parse.quote(f"{cidade},{estado}")
        
        while pagina <= limite_paginas:
            if pagina == 1:
                guiamais_url = f"https://www.guiamais.com.br/encontre?searchbox=true&what={segmento_codificado}&where={cidade_estado_codificado}"
            else:
                guiamais_url = f"https://www.guiamais.com.br/encontre?searchbox=true&what={segmento_codificado}&where={cidade_estado_codificado}&p={pagina}"

            print(f"\n--- Acessando GuiaMais URL da página {pagina}: {guiamais_url} ---")
            driver.get(guiamais_url)

            # --- Lidar com o pop-up de cookies do GuiaMais ---
            try:
                accept_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-green[data-action='accept']"))
                )
                print("  > Botão 'Aceitar Cookies' do GuiaMais encontrado. Clicando...")
                accept_button.click()
                time.sleep(random.uniform(1, 2)) 
            except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                pass 
            except Exception as e:
                print(f"  > Erro ao tentar fechar pop-up de cookies do GuiaMais: {e}")

            # --- Esperar o conteúdo principal do GuiaMais carregar ---
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'card'))
                )
                print(f"  > Conteúdo da página {pagina} do GuiaMais carregado.")
            except TimeoutException:
                print(f"  > Tempo limite excedido ao carregar o conteúdo da página {pagina} do GuiaMais. Pode não haver resultados.")
                break 
            
            # Pega todos os elementos de card de empresa no Selenium
            selenium_company_cards = driver.find_elements(By.CLASS_NAME, 'card')
            
            if not selenium_company_cards:
                print(f"Nenhum card de empresa encontrado na página {pagina} do GuiaMais.")
                if pagina == 1:
                    print("Verifique se o segmento, cidade e estado estão corretos no GuiaMais.")
                break 

            for card_index, selenium_card in enumerate(selenium_company_cards):
                nome_fantasia = "N/A"
                endereco_completo = "N/A"
                telefone_final = "N/A" 

                # Extrair nome e endereço do GuiaMais
                try:
                    nome_h2 = selenium_card.find_element(By.CLASS_NAME, 'aTitle')
                    nome_a = nome_h2.find_element(By.TAG_NAME, 'a')
                    nome_fantasia = nome_a.text.strip()
                except NoSuchElementException:
                    pass 

                if nome_fantasia == "N/A" or not nome_fantasia:
                    print(f"  - Nome Fantasia não encontrado para um card. Pulando este registro.")
                    continue 

                try:
                    endereco_tag = selenium_card.find_element(By.CLASS_NAME, 'advAddress')
                    endereco_completo = endereco_tag.text.strip().replace('\n', ' ').replace('  ', ' ')
                except NoSuchElementException:
                    pass 
                
                print(f"  Processando: {nome_fantasia}")

                # --- Lógica de EXTRAÇÃO de telefone: Prioridade 1: WhatsApp ---
                whatsapp_found_and_valid = False
                try:
                    whatsapp_link_element = selenium_card.find_element(By.CSS_SELECTOR, "a.btn-whatsapp-inversed")
                    
                    whatsapp_url = whatsapp_link_element.get_attribute('href')
                    
                    if whatsapp_url:
                        parsed_url = urllib.parse.urlparse(whatsapp_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        whatsapp_number = query_params.get('phone', [''])[0] 
                        
                        if whatsapp_number and whatsapp_number.strip(): 
                            telefone_final = f"WhatsApp: {whatsapp_number}"
                            whatsapp_found_and_valid = True
                        else:
                            print(f"    > WhatsApp encontrado para {nome_fantasia}, mas número vazio.")
                    else:
                        print(f"    > Link WhatsApp vazio para {nome_fantasia}.")
                except NoSuchElementException:
                    print(f"    > Link WhatsApp não encontrado para {nome_fantasia}.")
                except TimeoutException:
                    print(f"    > Tempo limite ao tentar encontrar link WhatsApp para {nome_fantasia}.")
                except Exception as e:
                    print(f"    > Erro ao tentar extrair WhatsApp para {nome_fantasia}: {e}.")

                # --- Lógica de EXTRAÇÃO de telefone: Prioridade 2: Botão Ligar (se WhatsApp não encontrado/válido) ---
                if not whatsapp_found_and_valid:
                    try:
                        telefone_container = None
                        try:
                            telefone_container = selenium_card.find_element(By.CLASS_NAME, 'language__menu.telefone__menu')
                        except NoSuchElementException:
                            pass 

                        if telefone_container:
                            ligar_button = telefone_container.find_element(By.CSS_SELECTOR, "button.language__toggle.btn.btn-block.btn-gray.text-black")
                            
                            # Rola até o botão (ainda importante para garantir que o elemento esteja pronto)
                            driver.execute_script("arguments[0].scrollIntoView();", ligar_button)
                            
                            # NOVO: Tentar clicar via JavaScript para evitar interceptação
                            driver.execute_script("arguments[0].click();", ligar_button)
                            
                            WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, ".language__menu.telefone__menu .phone__list"))
                            )
                            time.sleep(random.uniform(0.5, 1.5)) 
                            
                            telefone_container_soup = BeautifulSoup(telefone_container.get_attribute('outerHTML'), 'html.parser')

                            telefones_list = []
                            lista_telefones_ul = telefone_container_soup.find('ul', class_='phone__list')
                            if lista_telefones_ul:
                                for tel_item in lista_telefones_ul.find_all('a', href=True):
                                    if tel_item['href'].startswith('tel:'):
                                        telefone_numero = tel_item.get_text(strip=True)
                                        if telefone_numero:
                                            telefones_list.append(telefone_numero)
                            
                            telefone_final = ", ".join(telefones_list) if telefones_list else "N/A (Ligar sem números)"
                            if telefone_final != "N/A (Ligar sem números)":
                                print(f"    > Telefone(s) do GuiaMais (Ligar) encontrado(s): {telefone_final}")
                        else:
                            print(f"    > Nem WhatsApp válido, nem Botão Ligar disponível para {nome_fantasia}.")

                    except TimeoutException:
                        print(f"    > Tempo limite ao tentar clicar ou esperar a lista de telefones para: {nome_fantasia}.")
                        telefone_final = "N/A (Timeout Ligar/Lista)"
                    except NoSuchElementException:
                        print(f"    > Elemento de telefone (botão ou lista) não encontrado para: {nome_fantasia}.")
                        telefone_final = "N/A (Elemento não encontrado)"
                    except ElementNotInteractableException as e:
                        print(f"    > ERRO: Botão 'Ligar' foi interceptado novamente (JS Click falhou?): {e}")
                        telefone_final = "N/A (Ligar Interceptado)"
                    except Exception as e:
                        print(f"    > Erro inesperado ao processar telefone via Ligar para {nome_fantasia}: {e}")
                        telefone_final = f"N/A (Erro ao processar tel: {e})"

                # Se o telefone ainda for N/A após todas as tentativas no GuiaMais
                if telefone_final.startswith("N/A"):
                    telefone_final = "N/A (Não encontrado no GuiaMais)" # Mensagem mais clara

                dados_coletados.append({
                    'Nome Fantasia': nome_fantasia,
                    'Endereço Completo': endereco_completo,
                    'Telefone': telefone_final 
                })
                
            pagina += 1 
            time.sleep(random.uniform(3, 7)) # Delay maior entre as páginas do GuiaMais

    except WebDriverException as e:
        print(f"Erro no WebDriver: {e}")
        print("Certifique-se de que o chromedriver está no PATH ou na pasta do projeto e compatível com a versão do Chrome.")
        print("Tente rodar sem '--headless' para depurar visualmente: comente a linha 'options.add_argument('--headless')'")
    except Exception as e:
        print(f"Ocorreu um erro inesperado na função principal: {e}")
    finally:
        if driver:
            driver.quit()
            print("WebDriver encerrado.")

    print(f"\nScraping concluído. Total de empresas coletadas: {len(dados_coletados)}")
    return dados_coletados

# Exemplo de como você poderia testar a função diretamente (opcional)
if __name__ == '__main__':
    print("Testando a função scrape_guiamais (Apenas GuiaMais: WhatsApp > Ligar)...")
    dados = scrape_guiamais('BA', 'Salvador', 'Pizzaria')
    if dados:
        df = pd.DataFrame(dados)
        print("\n--- Primeiros 5 resultados coletados: ---")
        print(df.head())
        
        # Salvando como XLSX
        df.to_excel("dados_guiamais_final_simples.xlsx", index=False)
        print(f"\nDados salvos em dados_guiamais_final_simples.xlsx")
    else:
        print("\nNenhum dado foi coletado (ou todos foram filtrados por não ter nome fantasia).")