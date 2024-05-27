from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os
from email.message import EmailMessage
import ssl
import smtplib
from datetime import datetime

url = 'https://investidor10.com.br/fiis/rankings/maior-valor-patrimonial/'

# Setup do ChromeDriver
service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)
driver.get(url)

# Usando o click para poder interagir com a página e colocar os filtros necessários
button = driver.find_element(By.XPATH, '//*[@id="page-ranking"]/section[1]/div/div/div[1]/div[3]/a')
button.click()
filter1 = driver.find_element(By.XPATH, '//*[@id="swal2-content"]/div/div[5]/div/label')
filter1.click()
filter2 = driver.find_element(By.XPATH, '//*[@id="swal2-content"]/div/div[6]/div/label')
filter2.click()
wait = WebDriverWait(driver, 10)
quit_section = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[16]/div/div[1]/button')))
quit_section.click()

# Coloquei um sleep de 2 segundos para evitar caso ele tentar pegar o HTML do modal dos filtros
time.sleep(2)

# Pega o HTML do site com os filtros já aplicados
page_source = driver.page_source

soup = BeautifulSoup(page_source, 'html.parser')
rows = soup.find_all('tr', role='row')

dict_keys = ['Ticker','Patrimônio Líquido', 'DY atual', 'P/VP', 'Liquidez Diária', 'Variação (12 meses)', 'Tipo de Fundo', 'Segmento']
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

# Processo para fazer o envio do e-mail
email_sender = 'ranking.investidor10@gmail.com'
email_password = os.environ.get("PASSWORD")
email_reciever = 'gabriellbona@gmail.com'

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

context = ssl.create_default_context()

with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
    smtp.login(email_sender, email_password)
    smtp.sendmail(email_sender, email_reciever, em.as_string())