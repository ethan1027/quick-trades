import os
import pickle
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs

username = os.environ["USERNAME"]
password = os.environ["PASSWORD"]
redirect_url = os.environ["REDIRECT_URL"]


def signin(url):
  options = webdriver.ChromeOptions()
  options.add_argument("--user-data-dir=C:\\Users\\quane\\Documents\\GitProjects\\py-quick-trades\\user_data")
  driver = webdriver.Chrome(options=options)
  driver.get(url)
  if 'login' in driver.current_url:
    print('entering credentials')
    username_element = driver.find_element(By.ID, "username")
    username_element.send_keys(username)
    password_element = driver.find_element(By.ID, "password")
    password_element.send_keys(password)
    submit = driver.find_element(By.ID, "btn-login")
    submit.click()
  WebDriverWait(driver, 60).until(EC.url_contains(f"{redirect_url}/?code="))
  print(driver.current_url)
  parsed_url = urlparse(driver.current_url)
  qs = parse_qs(parsed_url.query)
  return qs["code"]