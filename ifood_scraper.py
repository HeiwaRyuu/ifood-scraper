from playwright.sync_api import Playwright, sync_playwright, expect
from bs4 import BeautifulSoup
import pandas as pd
import datetime as dt

def run(playwright: Playwright) -> None:
    address = "Avenida Joao XXIII Saraiva"
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.ifood.com.br/")
    page.get_by_placeholder("Em qual endereço você está?").click()
    page.get_by_role("button", name="Buscar endereço e número").click()
    page.get_by_role("textbox", name="Buscar endereço e número").fill(address)
    page.locator("[data-test-id=\"button-address-EkpBdmVuaWRhIEpvw6NvIFhYSUlJIC0gU2FyYWl2YSwgVWJlcmzDom5kaWEgLSBTdGF0ZSBvZiBNaW5hcyBHZXJhaXMsIEJyYXppbCIuKiwKFAoSCUOjWq0LRaSUEdbe7n3KRJrbEhQKEgnzUTssEEWklBFxZ2RXqQDEkw\"]").get_by_role("button").click()
    page.get_by_label("Número", exact=True).click()
    page.get_by_label("Número", exact=True).fill("438")
    page.get_by_role("button", name="Buscar com número").click()
    page.get_by_role("button", name="Confirmar localização").click()
    page.get_by_role("button", name="Salvar endereço").click()
    page.get_by_role("link", name="Restaurantes").click()

    counter = 0
    text_selector = 'text="Ver mais"'
    while(True):
        try:
            page.wait_for_selector(text_selector)
            page.click(text_selector)
            counter += 1
        except:
            print(f"Counter for 'Ver mais' button pressed: {counter}")
            break

    merchants = page.locator(".merchant-list-v2__wrapper")
    html = merchants.inner_html()
    soup = BeautifulSoup(html, "html.parser")

    # Find all elements with the class "merchant-list-v2__item-wrapper"
    item_wrappers = soup.find_all(class_="merchant-list-v2__item-wrapper")
    date_and_time = dt.datetime.now()
    date_lst = []
    code_lst = []
    address_lst = []
    name_lst = []
    scrape_time_lst = []
    rating_lst = []
    classification_lst = []
    have_photo_lst = []
    distance_lst = []
    delivery_fee = []
    for index, item in enumerate(item_wrappers):
        # Extract text from elements within the item wrapper
        merchant_name = item.find(class_="merchant-v2__name").get_text(strip=True) if item.find(class_="merchant-v2__name") else "Sem Nome"
        info = item.find(class_="merchant-v2__info").get_text(strip=True) if item.find(class_="merchant-v2__info") else "Sem Informação"
        try:
            rating, classification, distance = info.split("•")
        except:
            try:
                classification, distance = info.split("•")
                rating = "Sem Informação"
            except:
                rating = "Sem Informação"
                classification = "Sem Informação"
                distance = "Sem Informação"
        have_photo = "Sim" if item.find(class_="cardstack-image") else "Não"
        footer_info = item.find(class_="merchant-v2__footer").get_text(strip=True) if item.find(class_="merchant-v2__footer") else "Sem Informação"
        delivery_fee_str = "0" if "Grátis" in footer_info else footer_info.split("•")[-1].replace("R$", "").replace(",", ".")[1:]

        try:
            rating = eval(rating)
        except:
            rating = "Sem Informação (Novidade)"
        try:
            distance = eval(distance.split(" ")[0])
        except:
            distance = "Sem Informação"
        try:
            delivery_fee_str = eval(delivery_fee_str)
        except:
            delivery_fee_str = "Sem Informação"

        date_lst.append(date_and_time.strftime("%d/%m/%Y"))
        code_lst.append(index+1)
        address_lst.append(address)
        name_lst.append(merchant_name)
        scrape_time_lst.append(date_and_time.strftime("%H:%M"))
        rating_lst.append(rating)
        classification_lst.append(classification)
        have_photo_lst.append(have_photo)
        distance_lst.append(distance)
        delivery_fee.append(delivery_fee_str)

    data = {"data":date_lst, "codigo_estabelecimento":code_lst, "endereco_universidade":address_lst, 
            "nome_restaurante":name_lst, "categoria":classification_lst, "horario_coleta":scrape_time_lst, 
            "score_estrela":rating_lst, "foto":have_photo_lst, "distancia":distance_lst, 
            "taxa_entrega":delivery_fee}
    df = pd.DataFrame(data)
    df.to_excel("ifood_data.xlsx", index=False)

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)