from playwright.sync_api import Playwright, sync_playwright
from playwright.sync_api import TimeoutError
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import concurrent.futures
from bs4 import BeautifulSoup
import json
import pandas as pd
import datetime as dt
import time
import os
import random


DEFAULT_TIMEOUT = 2
MAX_ERROR_TRIES = 3
MAX_THREADS = 1
USE_PROXY = False

def generate_df(merchants, address):
    try:
        html = merchants.inner_html()
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"Exception: {e}")
        data = {"empty":[]}
        return pd.DataFrame(data)

    date_lst = []
    code_lst = []
    address_lst = []
    name_lst = []
    scrape_time_lst = []
    rating_lst = []
    classification_lst = []
    # have_photo_lst = []
    delivery_time_lst = []
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
        # have_photo = "Sim" if item.find(class_="cardstack-image").find("img") else "Não"
        footer_info = item.find(class_="merchant-v2__footer").get_text(strip=True) if item.find(class_="merchant-v2__footer") else "Sem Informação"
        delivery_time = footer_info.split("•")[-2]
        status = "Aberto" if ("min" in delivery_time) else "Fechado"
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


        date_and_time = dt.datetime.now()
        date_lst.append(date_and_time.strftime("%d/%m/%Y"))
        code_lst.append(index+1)
        address_lst.append(address)
        name_lst.append(merchant_name)
        scrape_time_lst.append(date_and_time.strftime("%H:%M"))
        status_lst.append(status)
        rating_lst.append(rating)
        classification_lst.append(classification)
        # have_photo_lst.append(have_photo)
        delivery_time_lst.append(delivery_time)
        distance_lst.append(distance)
        delivery_fee_lst.append(delivery_fee)

    data = {"data":date_lst, "codigo_estabelecimento":code_lst, "endereco_universidade":address_lst, 
    "nome_restaurante":name_lst, "categoria":classification_lst, "horario_coleta":scrape_time_lst, "status":status_lst, 
    "score_estrela":rating_lst, "tempo_entrega":delivery_time_lst, "distancia":distance_lst, 
    "taxa_entrega":delivery_fee_lst}
    df = pd.DataFrame(data)
    return df


def fetch_merchants(page, number_of_pages, only_open=False):
    counter = 0
    button_selector = ".cardstack-nextcontent > button:first-of-type"
    selector = 'section.cardstack-section[data-card-name="NEXT_CONTENT"]'
    flag_end_of_page = False
    time.sleep(DEFAULT_TIMEOUT*2)
    while(True):
        if only_open:
            merchants = page.locator(".merchant-list-v2__wrapper")
            try:
                html = merchants.inner_html()
                soup = BeautifulSoup(html, "html.parser")
            except Exception as e:
                print(f"Exception: {e}")
                continue
            item_wrappers = soup.find_all(class_="merchant-list-v2__item-wrapper")
            last_merchant = item_wrappers[-1]
            footer_info = last_merchant.find(class_="merchant-v2__footer").get_text(strip=True) if last_merchant.find(class_="merchant-v2__footer") else "Sem Informação"
            delivery_time = footer_info.split("•")[-2]
            status = "Aberto" if ("min" in delivery_time) else "Fechado"
            if status == "Fechado":
                print("Closed Restaurant Has been found!")
                print(f"Counter for 'Ver mais' button pressed: {counter}\nTotal of {counter+1} pages.")
                return True
        
        try:
            time.sleep(DEFAULT_TIMEOUT)
            flag_end_of_page = not page.query_selector(selector)
            if(flag_end_of_page):
                print("Reached end of page...")
                print(f"Counter for 'Ver mais' button pressed: {counter}\nTotal of {counter+1} pages.")
                break
            page.click(button_selector)
        except Exception as e:
            ## THIS ONLY HAPPENS WHEN WHILE FAILS TO CHECK IT HAS REACHED THE END
            ## AND WHEN TRYING TO CLICK BUTTON FAILS BECAUSE BUTTON NO LONGER EXISTS
            ## THEREFORE WE RETURN TRUE
            if(flag_end_of_page):
                print("Reached end of page...")
                print(f"Counter for 'Ver mais' button pressed: {counter}\nTotal of {counter+1} pages.")
                break
            print(f"Exception: {e}")
            return False
        counter += 1
        if(number_of_pages!="ALL"):
            if(counter>=number_of_pages):
                print(f"Counter for 'Ver mais' button pressed: {counter}\nTotal of {counter+1} pages.")
                return True
    return True

def fetch_proxy():
    with open("proxy.json", "r", encoding="utf-8") as fd:
        proxy_data = json.load(fd)
    return proxy_data

def random_ua(k=1):
    # returns a random useragent from the latest user agents strings list, weighted
    # according to observed prevalance
    ua_pct = {"ua": {"0": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36", "1": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0", "2": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36", "3": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0", "4": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36", "5": "Mozilla/5.0 (X11; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0", "6": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36", "7": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36", "8": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36", "9": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15", "10": "Mozilla/5.0 (X11; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0", "11": "Mozilla/5.0 (Windows NT 10.0; rv:105.0) Gecko/20100101 Firefox/105.0", "12": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0", "13": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0", "14": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}, "pct": {"0": 28.8, "1": 13.28, "2": 10.98, "3": 8.55, "4": 6.25, "5": 5.56, "6": 4.53, "7": 4.27, "8": 3.57, "9": 2.93, "10": 2.99, "11": 2.55, "12": 2.44, "13": 1.7, "14": 1.59}}
    return random.choices(list(ua_pct['ua'].values()), list(ua_pct['pct'].values()), k=k)

def scrape_address(row):
    print(row)
    error_lst = []
    address = row["ENDERECO"]
    number = str(row["NUMERO"])
    number_of_pages = str(row["NUMERO_DE_PAGINAS"])
    with sync_playwright() as playwright:
        try:
            number = str(eval(number))
        except Exception as e:
            print(f"Exception number: {e} - number being set to 'S/N'")
            number = "S/N"
        try:
            number_of_pages = eval(number_of_pages)
        except Exception as e:
            print(f"Exception number_of_pages: {e} - number_of_pages being set to 'ALL'")
            number_of_pages = "ALL"

        print(f"{address} | {number} | {number_of_pages}")
        tries = 0
        flag_success = False
        proxy = fetch_proxy()
        while(tries < MAX_ERROR_TRIES and not flag_success):
            url = "https://www.ifood.com.br"
            user_agent = random_ua()[0] # FETCH RANDOM USER AGENT EVERY SESSION
            if USE_PROXY:
                browser = playwright.chromium.launch(headless=True, proxy=proxy)
            else:
                browser = playwright.chromium.launch(headless=False)
            context = browser.new_context(user_agent=user_agent)
            page = context.new_page()
            try:
                page.goto(url)
                page.get_by_placeholder("Em qual endereço você está?").click()
                page.get_by_role("button", name="Buscar endereço e número").click()
                page.get_by_role("textbox", name="Buscar endereço e número").fill(address)

                selector = ".address-search-list > li:first-of-type"
                page.wait_for_selector(selector)
                page.locator(selector).click()
            except Exception as e:
                print(f"Exception: {e}")
                tries += 1
                if (tries>= MAX_ERROR_TRIES) and (address not in error_lst): error_lst.append(address)
                context.close()
                browser.close()
                continue

            try:
                time.sleep(DEFAULT_TIMEOUT)
                selector = 'button:has-text("Confirmar localização")'
                if(not page.query_selector(selector)): ## CHECKING IF "CONFIRMAR LOCALIZAÇÃO" IS ALREADY VISIBLE, IF SO, SKIP NUMBER INSERTION
                    selector = "input.form-input__field"
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
                if (tries>= MAX_ERROR_TRIES) and (address not in error_lst): error_lst.append(address)
                context.close()
                browser.close()
                continue
            
            try:
                # Abort based on the request type | ABORTING ANY IMAGE/CSS LOADING
                page.route("**/*", lambda route: route.abort() if (route.request.resource_type == "image" or route.request.resource_type == "stylesheet") else route.continue_())
                page.goto("https://www.ifood.com.br/restaurantes")
            except Exception as e:
                print(f"Exception: {e}")
                tries += 1
                if (tries>= MAX_ERROR_TRIES) and (address not in error_lst): error_lst.append(address)
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
                if (tries>= MAX_ERROR_TRIES) and (address not in error_lst): error_lst.append(address)
                tries += 1
                context.close()
                browser.close()
                continue

            ## FETCH MERCHANTS DATA
            merchants = page.locator(".merchant-list-v2__wrapper")
            if merchants:
                df = generate_df(merchants, address)
                if not df.empty:
                    print(f"OK - df with contents on {address}")
                else:
                    print(f"No HTML on {address}")
                    if (tries>= MAX_ERROR_TRIES) and (address not in error_lst): error_lst.append(address)
            # ---------------------
            context.close()
            browser.close()
            flag_success = True

    # SAVING EACH ISOLATED FILE SO WE CAN HAVE A BACKUP OF THOSE WHICH ACTUALLY WORKED!
    filename = f"ifood_data_{dt.datetime.now().strftime('%d-%m-%Y--%H-%M')}-{address}.xlsx"
    df.to_excel(f"coletas\\{filename}", sheet_name="INFO_RESTAURANTES", index=False)

    return [df, error_lst]

def main():
    df_lst = []
    error_lst = []
    df_enderecos = pd.read_excel("enderecos.xlsx", sheet_name="ENDERECOS")
    df_enderecos = df_enderecos[df_enderecos["COLETAR"]=="S"]
    
    with ThreadPoolExecutor(MAX_THREADS) as executor:
        # Submitting each row to the executor as a future
        futures = [executor.submit(scrape_address, row) for idx, row in df_enderecos.iterrows()]

    # Collecting results as they are completed
    for future in concurrent.futures.as_completed(futures):
        try:
            # Appending the result dataframe to the list
            df_lst.append(future.result()[0])   
            error_lst.append(future.result()[1])
            error_lst = [x for xs in error_lst for x in xs]
            print("COMEÇA AQUI")
            print(type(df_lst))
            print(df_lst)
            print(type(error_lst))
            print(error_lst)
        except Exception as e:
            print(f"Error processing row: {e}")
            
    # df_lst, error_lst = scrape_address(df_enderecos.iloc[[0]])

    if(df_lst):
        df = pd.concat(df_lst)
        if(not os.path.exists(f"{os.curdir}\\coletas")):
            os.mkdir(f"{os.curdir}\\coletas")
        filename = f"ifood_data_{dt.datetime.now().strftime('%d-%m-%Y--%H-%M')}.xlsx"
        df.to_excel(f"coletas\\{filename}", sheet_name="INFO_RESTAURANTES", index=False)
    else:
        print("An Error has occurred in all addresses fetching task. Please, retry.")

    with open("enderecos_com_erro.txt", "w") as f:
        if(error_lst):
            f.write(str(error_lst))
        else:
            f.write("Nenhum erro durante a coleta!")
        
if __name__ == "__main__":
    main()