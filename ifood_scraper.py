from playwright.sync_api import Playwright, sync_playwright, expect
from bs4 import BeautifulSoup
import pandas as pd
import datetime as dt
import time
import os

DEFAULT_TIMEOUT = 2
MAX_ERROR_TRIES = 3

def generate_df(merchants, address):
    try:
        html = merchants.inner_html()
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"Exception: {e}")
        data = {"empty":[]}
        return pd.DataFrame(data)

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
    status_lst = []
    delivery_fee_lst = []
    
    item_wrappers = soup.find_all(class_="merchant-list-v2__item-wrapper")
    for index, item in enumerate(item_wrappers):
        merchant_name = item.find(class_="merchant-v2__name").get_text(strip=True) if item.find(class_="merchant-v2__name") else "Sem Nome"
        info = item.find(class_="merchant-v2__info").get_text(strip=True) if item.find(class_="merchant-v2__info") else "Sem Informação"
        ## IF RESTAURANT HAS ALL 3 INFOS
        try:
            rating, classification, distance = info.split("•")
        except:
            ## IF RESTAURANT DOES NOT HAVE RATINGS YET
            try:
                classification, distance = info.split("•")
                rating = "Sem Informação"
            except:
                ## IF FOR SOME REASON, NO INFO IS AVAILABLE
                rating = "Sem Informação"
                classification = "Sem Informação"
                distance = "Sem Informação"
        have_photo = "Sim" if item.find(class_="cardstack-image").find("img") else "Não"
        footer_info = item.find(class_="merchant-v2__footer").get_text(strip=True) if item.find(class_="merchant-v2__footer") else "Sem Informação"
        status = "Fechado" if "Fechado" in footer_info else "Aberto"
        delivery_fee = "0" if "Grátis" in footer_info else footer_info.split("•")[-1].replace("R$", "").replace(",", ".")[1:]

        try:
            rating = eval(rating)
        except:
            rating = "Sem Informação (Novidade)"
        try:
            distance = eval(distance.split(" ")[0])
        except:
            distance = "Sem Informação"
        try:
            delivery_fee = eval(delivery_fee)
        except:
            delivery_fee = "Sem Informação"

        date_lst.append(date_and_time.strftime("%d/%m/%Y"))
        code_lst.append(index+1)
        address_lst.append(address)
        name_lst.append(merchant_name)
        scrape_time_lst.append(date_and_time.strftime("%H:%M"))
        status_lst.append(status)
        rating_lst.append(rating)
        classification_lst.append(classification)
        have_photo_lst.append(have_photo)
        distance_lst.append(distance)
        delivery_fee_lst.append(delivery_fee)

    data = {"data":date_lst, "codigo_estabelecimento":code_lst, "endereco_universidade":address_lst, 
    "nome_restaurante":name_lst, "categoria":classification_lst, "horario_coleta":scrape_time_lst, "status":status_lst, 
    "score_estrela":rating_lst, "foto":have_photo_lst, "distancia":distance_lst, 
    "taxa_entrega":delivery_fee_lst}
    df = pd.DataFrame(data)
    return df


def fetch_merchants(page, number_of_pages):
    counter = 0
    button_selector = ".cardstack-nextcontent > button:first-of-type"
    selector = 'section.cardstack-section[data-card-name="NEXT_CONTENT"]'
    while(True):
        try:
            time.sleep(DEFAULT_TIMEOUT)
            if(not page.query_selector(selector)):
                print("Reached end of page...")
                break
            page.click(button_selector)
        except Exception as e:
            ## THIS ONLY HAPPENS WHEN WHILE FAILS TO CHECK IT HAS REACHED THE END
            ## AND WHEN TRYING TO CLICK BUTTON FAILS BECAUSE BUTTON NO LONGER EXISTS
            ## THEREFORE WE RETURN TRUE
            if(not page.query_selector(selector)):
                print("Reached end of page...")
                break
            print(page.query_selector(selector))
            print(f"Exception HERE: {e}")
            return False
        counter += 1
        if(number_of_pages!="ALL"):
            if(counter>=number_of_pages):
                print(f"Counter for 'Ver mais' button pressed: {counter}\nTotal of {counter+1} pages.")
                return True
    return True


def run(playwright: Playwright) -> None:
    df_lst = []
    error_lst = []
    df_enderecos = pd.read_excel("enderecos.xlsx", sheet_name="ENDERECOS")
    df_enderecos = df_enderecos[df_enderecos["COLETAR"]=="S"]
    for _, row in df_enderecos.iterrows():
        address = row["ENDERECO"]
        number = str(row["NUMERO"])        
        number_of_pages = str(row["NUMERO_DE_PAGINAS"])
        try:
            number = str(eval(number))
        except Exception as e:
            print(f"Exception: {e}")
            number = "S/N"
        try:
            number_of_pages = eval(number_of_pages)
        except Exception as e:
            print(f"Exception: {e}")
            number_of_pages = "ALL"

        print(f"{address} | {number} | {number_of_pages}")
        tries = 0
        flag_success = False
        while(tries < MAX_ERROR_TRIES and not flag_success):
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto("https://www.ifood.com.br/")
                page.get_by_placeholder("Em qual endereço você está?").click()
                page.get_by_role("button", name="Buscar endereço e número").click()
                page.get_by_role("textbox", name="Buscar endereço e número").fill(address)

                selector = ".address-search-list > li:first-of-type"
                page.wait_for_selector(selector)
                page.locator(selector).click()
            except Exception as e:
                print(f"Exception: {e}")
                tries += 1
                if address not in error_lst: error_lst.append(address)
                context.close()
                browser.close()
                continue

            try:
                time.sleep(DEFAULT_TIMEOUT)
                selector = "input.form-input__field"
                if(page.query_selector(selector)):
                    element = page.wait_for_selector(selector)
                    element.click()
                    element.fill(number)
                    page.get_by_role("button", name="Buscar com número").click()
            except:
                print("No number required for this address...")
            
            try:
                time.sleep(DEFAULT_TIMEOUT)
                selector = 'button:has-text("Confirmar localização")'
                page.locator(selector).click()
                page.get_by_role("button", name="Salvar endereço").click()
            except Exception as e:
                print(f"Exception: {e}")
                tries += 1
                if address not in error_lst: error_lst.append(address)
                context.close()
                browser.close()
                continue
            
            try:
                page.goto("https://www.ifood.com.br/restaurantes")
            except Exception as e:
                print(f"Exception: {e}")
                tries += 1
                if address not in error_lst: error_lst.append(address)
                context.close()
                browser.close()
                continue

            ## LOOP THROUGH ALL PAGES
            try_count = 0
            while(try_count < MAX_ERROR_TRIES):
                merchants_status = fetch_merchants(page, number_of_pages)
                if merchants_status:
                    break
                try_count += 1
            if(try_count >= MAX_ERROR_TRIES):
                print(f"Max tries exceeded for looping merchants on {address}")
                if address not in error_lst: error_lst.append(address)
                tries += 1
                context.close()
                browser.close()
                continue

            ## FETCH MERCHANTS DATA
            merchants = page.locator(".merchant-list-v2__wrapper")
            if merchants:
                df = generate_df(merchants, address)
                if not df.empty:
                    df_lst.append(df)
                else:
                    print(f"No HTML on {address}")
                    if address not in error_lst: error_lst.append(address)
            # ---------------------
            context.close()
            browser.close()
            flag_success = True

    if(df_lst):
        df = pd.concat(df_lst)
        if(not os.path.exists(f"{os.curdir}\\coletas")):
            os.mkdir(f"{os.curdir}\\coletas")
        df.to_excel(f"coletas\\ifood_data_{dt.datetime.now().strftime("%d-%m-%Y--%H-%M")}.xlsx", sheet_name="INFO_RESTAURANTES", index=False)
    else:
        print("An Error has occurred in all addresses fetching task. Please, retry.")

    with open("error_addresses.txt", "w") as f:
        f.write(str(error_lst))


with sync_playwright() as playwright:
    run(playwright)