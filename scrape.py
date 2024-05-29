from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
from email.message import EmailMessage
import ssl
import smtplib
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager

url = 'https://investidor10.com.br/fiis/rankings/maior-valor-patrimonial/'

# Setup do ChromeDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode for CI environment
options.add_argument("--no-sandbox")  # Bypass OS security model
options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

driver = webdriver.Chrome(service=service, options=options)
driver.get(url)

# Usando o click para poder interagir com a página e colocar os filtros necessários
try:
    button = WebDriverWait(driver, 180).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="page-ranking"]/section[1]/div/div/div[1]/div[3]/a'))
    )
    button.click()
    
    filter1 = WebDriverWait(driver, 180).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="swal2-content"]/div/div[5]/div/label'))
    )
    filter1.click()
    
    filter2 = WebDriverWait(driver, 180).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="swal2-content"]/div/div[6]/div/label'))
    )
    filter2.click()

    close_button = driver.find_element(By.CLASS_NAME, 'swal2-close')
    close_button.click()

except Exception as e:
    print(f"Error interacting with page elements: {e}")
    driver.quit()
    raise

# Coloquei um sleep de 2 segundos para evitar caso ele tentar pegar o HTML do modal dos filtros
time.sleep(2)

# Pega o HTML do site com os filtros já aplicados
page_source = driver.page_source

soup = BeautifulSoup(page_source, 'html.parser')
rows = soup.find_all('tr', role='row')

dict_keys = ['Ticker', 'Patrimônio Líquido', 'DY atual', 'P/VP', 'Liquidez Diária', 'Variação (12 meses)', 'Tipo de Fundo', 'Segmento']
data = []

for row in rows:
    cells = row.find_all('td')
    cell_texts = [cell.get_text(strip=True) for cell in cells]
    row_dict = dict(zip(dict_keys, cell_texts))
    data.append(row_dict)

file_today = datetime.now().strftime('%d-%m-%Y')

df = pd.DataFrame(data)
df = df.dropna(how='all')
df.to_excel(f'ranking_{file_today}.xlsx', index=False)

driver.quit()
time.sleep(1)

# Vamos começar daqui o novo scraping, de fundos e ações específicas.
acoes = ['BBAS3', 'BBSE3', 'CSMG3']
data_acoes_list = []

for acao in acoes:
    url_acoes = f'https://investidor10.com.br/acoes/{acao}/'

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode for CI environment
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url_acoes)

    page_source = driver.page_source

    soup = BeautifulSoup(page_source, 'html.parser')
    card_body = soup.find_all(class_='_card-body')

    data_acoes = {}
    acoes_keys = ['Cotação', 'Variação (12 meses)', 'P/L', 'P/VP', 'DY']

    for i, box in enumerate(card_body):
        if i >= len(acoes_keys):
            break
        text = box.get_text().strip()
        data_acoes[acoes_keys[i]] = text

    data_acoes_list.append(data_acoes)

    driver.quit()
    time.sleep(1)

acoes_df = pd.DataFrame(data_acoes_list)
acoes_df.to_excel(f'acoes_{file_today}.xlsx', index=False)

# Processo para fazer o envio do e-mail
email_sender = 'ranking.investidor10@gmail.com'
email_password = os.environ.get("PASSWORD")
email_reciever = 'gabriellbonavina@gmail.com'

today = datetime.now().strftime('%d/%m/%Y')

subject = f'Ranking de FIIs de hoje ({today})'
body = f"""
Confira já o ranking dos FIIs de hoje ({today}) por meio desta tabela Excel feita pelo site Investidor 10.
"""

em = EmailMessage()
em['From'] = email_sender
em['To'] = email_reciever
em['Subject'] = subject
em.set_content(body)

file = f"ranking_{file_today}.xlsx"
with open(file, 'rb') as f:
    file_data = f.read()
    file_name = f.name
em.add_attachment(file_data, maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=file_name)

file2 = f"acoes_{file_today}.xlsx"
with open(file2, 'rb') as f:
    file_data = f.read()
    file_name = f.name
em.add_attachment(file_data, maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=file_name)

if email_password:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_reciever, em.as_string())
else:
    print("Email password not set in environment variables.")
