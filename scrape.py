from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager

url = 'https://investidor10.com.br/fiis/rankings/maior-valor-patrimonial/'

# Setup do ChromeDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

try:
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)

    # Apply filters
    button = WebDriverWait(driver, 180).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="page-ranking"]/section[1]/div/div/div[1]/div[3]/a'))
    )
    driver.execute_script('arguments[0].click();', button)

    for xpath in ['//*[@id="swal2-content"]/div/div[5]/div/label', '//*[@id="swal2-content"]/div/div[6]/div/label']:
        filter_element = WebDriverWait(driver, 180).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", filter_element)

    # Wait for the table to update after applying filters
    time.sleep(2)

    # Get the updated page source
    page_source = driver.page_source

except WebDriverException as e:
    print(f"Error during web scraping: {e}")
    exit(1)
finally:
    driver.quit()

# Parse the table
soup = BeautifulSoup(page_source, 'html.parser')
rows = soup.find_all('tr', role='row')

dict_keys = ['Ticker', 'Patrimônio Líquido', 'DY atual', 'P/VP', 'Liquidez Diária', 'Variação (12 meses)', 'Tipo de Fundo', 'Segmento']
data = []

for row in rows:
    cells = row.find_all('td')
    cell_texts = [cell.get_text(strip=True) for cell in cells]
    row_dict = dict(zip(dict_keys, cell_texts))
    data.append(row_dict)

df = pd.DataFrame(data)
df = df.dropna(how='all')

# Save to Excel (assuming you want to keep this part)
from datetime import datetime
file_today = datetime.now().strftime('%d-%m-%Y')
df.to_excel(f'ranking_{file_today}.xlsx', index=False)

driver.quit()
time.sleep(1)

# Vamos começar daqui o novo scraping, de fundos e ações específicas.
acoes = ['BBAS3', 'BBSE3', 'CSMG3', 'CXSE3', 'TAEE11', 'TRPL4']
acoes.sort()

data_acoes_list = []

for acao in acoes:
    url_acoes = f'https://investidor10.com.br/acoes/{acao}/'

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode for CI environment
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url_acoes)
        page_source = driver.page_source
    except WebDriverException as e:
        print(f"Error initializing WebDriver: {e}")
        continue
    finally:
        driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    card_body = soup.find_all(class_='_card-body')

    data_acoes = {}
    data_acoes['Ação'] = acao
    acoes_keys = ['Cotação', 'Variação (12 meses)', 'P/L', 'P/VP', 'DY']

    for i, box in enumerate(card_body):
        if i >= len(acoes_keys):
            break
        text = box.get_text().strip()
        data_acoes[acoes_keys[i]] = text

    data_acoes_list.append(data_acoes)

    time.sleep(1)

acoes_df = pd.DataFrame(data_acoes_list)

fiis = ['BTLG11', 'HGLG11', 'MXRF11', 'KNCR11', 'KNRI11', 'RZAK11', 'TGAR11', 'URPR11', 'VGHF11', 'VISC11', 'XPLG11', 'XPML11']
fiis.sort()

data_fiis_list = []

for fii in fiis:
    url_fiis = f'https://investidor10.com.br/fiis/{fii}/'

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode for CI environment
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url_fiis)
        page_source = driver.page_source
    except WebDriverException as e:
        print(f"Error initializing WebDriver: {e}")
        continue
    finally:
        driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    card_body = soup.find_all(class_='_card-body')

    data_fiis = {}
    data_fiis['FII'] = fii
    fiis_keys = ['Cotação', 'DY (12 meses)', 'P/VP', 'Liquidez Diária', 'Variação (12 meses)']

    for i, box in enumerate(card_body):
        if i >= len(fiis_keys):
            break
        text = box.get_text().strip()
        data_fiis[fiis_keys[i]] = text

    data_fiis_list.append(data_fiis)

    time.sleep(1)

fiis_df = pd.DataFrame(data_fiis_list)

writer = pd.ExcelWriter(f'acoes_e_fiis_{file_today}.xlsx', engine='xlsxwriter')
acoes_df.to_excel(writer, sheet_name='Ações', index=False)
fiis_df.to_excel(writer, sheet_name='FIIs', index=False)

writer.close()

# Processo para fazer o envio do e-mail
email_sender = os.environ.get("SENDER")
email_password = os.environ.get("PASSWORD")
email_reciever = os.environ.get("RECIEVER")

today = datetime.now().strftime('%d/%m/%Y')

subject = f'Ranking, suas ações e FIIs de hoje ({today})'
body = f"""
Confira já o ranking dos FIIs de hoje ({today}) por meio desta tabela Excel feita pelo site Investidor 10. Veja como estão suas ações e FII's hoje também!
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

file2 = f"acoes_e_fiis_{file_today}.xlsx"
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
